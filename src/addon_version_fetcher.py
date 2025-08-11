"""
EKS Addon Version Data Fetcher
Fetches and caches common addon version compatibility data for all EKS versions.
This data is cluster-independent and should be fetched once per assessment run.
"""

import json
import boto3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import click


@dataclass
class AddonVersionInfo:
    """Addon version information for a specific EKS version."""
    addon_name: str
    eks_version: str
    min_addon_version: str
    max_addon_version: str
    default_version: str
    addon_type: str  # 'core_aws', 'aws_managed', 'third_party'
    all_versions: List[str]
    publisher: str
    owner: str


class EKSAddonVersionFetcher:
    """Fetches and caches EKS addon version compatibility data."""
    
    def __init__(self, region: str = 'us-west-2'):
        self.region = region
        self.eks_client = boto3.client('eks', region_name=region)
        
    def fetch_all_addon_versions(self) -> Dict[str, Any]:
        """Fetch comprehensive addon version data for all EKS versions."""
        click.echo("🔍 Fetching comprehensive EKS addon version compatibility data...")
        
        # Get all supported EKS versions
        eks_versions = self._get_supported_eks_versions()
        click.echo(f"   📊 Found {len(eks_versions)} supported EKS versions: {', '.join(eks_versions)}")
        
        # Get all available addons
        available_addons = self._get_available_addons()
        click.echo(f"   🔧 Found {len(available_addons)} available addons: {', '.join(available_addons[:5])}...")
        
        # Build comprehensive compatibility matrix
        compatibility_matrix = {
            'metadata': {
                'generated_at': str(click.DateTime()),
                'region': self.region,
                'eks_versions': eks_versions,
                'total_addons': len(available_addons)
            },
            'addon_versions': {}
        }
        
        for eks_version in eks_versions:
            click.echo(f"   📊 Analyzing EKS version {eks_version}...")
            compatibility_matrix['addon_versions'][eks_version] = {}
            
            for addon_name in available_addons:
                try:
                    addon_info = self._get_addon_versions_for_eks_version(addon_name, eks_version)
                    if addon_info:
                        compatibility_matrix['addon_versions'][eks_version][addon_name] = addon_info
                except Exception as e:
                    click.echo(f"      ⚠️  Warning: Could not get addon info for {addon_name} on EKS {eks_version}: {e}")
        
        click.echo("✅ Addon version compatibility data fetched successfully")
        return compatibility_matrix
    
    def _get_supported_eks_versions(self) -> List[str]:
        """Get list of supported EKS versions."""
        try:
            # Get EKS versions from describe-addon-versions for a common addon
            response = self.eks_client.describe_addon_versions(addonName='vpc-cni')
            versions = set()
            
            for addon_version in response.get('addons', []):
                for compatibility in addon_version.get('compatibilities', []):
                    cluster_version = compatibility.get('clusterVersion')
                    if cluster_version:
                        versions.add(cluster_version)
            
            # Sort versions
            sorted_versions = sorted(list(versions), key=lambda x: [int(i) for i in x.split('.')])
            
            # If we still don't have versions, try a different approach
            if not sorted_versions:
                # Try getting versions from multiple addons
                common_addons = ['vpc-cni', 'coredns', 'kube-proxy']
                for addon in common_addons:
                    try:
                        response = self.eks_client.describe_addon_versions(addonName=addon)
                        for addon_data in response.get('addons', []):
                            for addon_version in addon_data.get('addonVersions', []):
                                for compatibility in addon_version.get('compatibilities', []):
                                    cluster_version = compatibility.get('clusterVersion')
                                    if cluster_version:
                                        versions.add(cluster_version)
                    except Exception:
                        continue
                
                sorted_versions = sorted(list(versions), key=lambda x: [int(i) for i in x.split('.')])
            
            return sorted_versions
            
        except Exception as e:
            click.echo(f"⚠️  Warning: Could not fetch EKS versions, using default list: {e}")
            return ['1.27', '1.28', '1.29', '1.30', '1.31', '1.32', '1.33']
    
    def _get_available_addons(self) -> List[str]:
        """Get list of all available EKS addons."""
        try:
            response = self.eks_client.describe_addon_versions()
            addon_names = []
            
            for addon in response.get('addons', []):
                addon_names.append(addon.get('addonName'))
            
            return list(set(addon_names))
            
        except Exception as e:
            click.echo(f"⚠️  Warning: Could not fetch addon list: {e}")
            return ['vpc-cni', 'coredns', 'kube-proxy', 'aws-ebs-csi-driver', 'aws-efs-csi-driver', 'aws-load-balancer-controller']
    
    def _get_addon_versions_for_eks_version(self, addon_name: str, eks_version: str) -> Optional[Dict[str, Any]]:
        """Get addon version information for a specific EKS version."""
        try:
            response = self.eks_client.describe_addon_versions(
                addonName=addon_name,
                kubernetesVersion=eks_version
            )
            
            if not response.get('addons'):
                return None
            
            addon_data = response['addons'][0]
            addon_versions = [av['addonVersion'] for av in addon_data.get('addonVersions', [])]
            
            if not addon_versions:
                return None
            
            # Determine addon type
            addon_type = self._determine_addon_type(addon_name)
            
            # Sort versions to find min/max
            sorted_versions = self._sort_addon_versions(addon_versions)
            
            return {
                'addon_name': addon_name,
                'eks_version': eks_version,
                'min_addon_version': sorted_versions[0] if sorted_versions else None,
                'max_addon_version': sorted_versions[-1] if sorted_versions else None,
                'default_version': addon_data.get('addonVersions', [{}])[0].get('addonVersion'),
                'all_versions': sorted_versions,
                'addon_type': addon_type,
                'publisher': addon_data.get('publisher', 'AWS'),
                'owner': addon_data.get('owner', 'aws')
            }
            
        except Exception as e:
            return None
    
    def _determine_addon_type(self, addon_name: str) -> str:
        """Determine the type of addon."""
        core_aws_addons = {
            'vpc-cni', 'coredns', 'kube-proxy', 'aws-ebs-csi-driver', 
            'aws-efs-csi-driver', 'aws-fsx-csi-driver'
        }
        
        aws_managed_addons = {
            'aws-load-balancer-controller', 'aws-for-fluent-bit', 
            'aws-cloudwatch-metrics', 'aws-node-termination-handler',
            'cluster-autoscaler', 'aws-distro-for-opentelemetry',
            'metrics-server', 'snapshot-controller'
        }
        
        if addon_name in core_aws_addons:
            return 'core_aws'
        elif addon_name in aws_managed_addons:
            return 'aws_managed'
        else:
            return 'third_party'
    
    def _sort_addon_versions(self, versions: List[str]) -> List[str]:
        """Sort addon versions in ascending order."""
        try:
            # Handle different version formats (semantic versioning)
            def version_key(version):
                # Remove 'v' prefix and split by '-' to handle versions like 'v1.12.6-eksbuild.2'
                clean_version = version.lstrip('v').split('-')[0]
                return [int(x) for x in clean_version.split('.')]
            
            return sorted(versions, key=version_key)
        except Exception:
            # Fallback to string sorting if version parsing fails
            return sorted(versions)
    
    def save_addon_versions_data(self, output_dir: str) -> str:
        """Fetch and save addon version data to a shared parent directory."""
        addon_versions_data = self.fetch_all_addon_versions()
        
        # Determine the parent directory for shared addon data
        output_path = Path(output_dir)
        
        # If output_dir is like "assessment-reports/629244530291-us-east-1-20250810-143449-assessment"
        # we want to save to "assessment-reports/shared-data/"
        if output_path.parent.name == "assessment-reports":
            # We're in a timestamped assessment directory, go to parent
            shared_data_dir = output_path.parent / "shared-data"
        elif output_path.name.startswith("assessment-reports"):
            # We're in the assessment-reports directory itself
            shared_data_dir = output_path / "shared-data"
        else:
            # For custom output directories, create a shared-data subdirectory
            shared_data_dir = output_path / "shared-data"
        
        shared_data_dir.mkdir(parents=True, exist_ok=True)
        
        addon_versions_file = shared_data_dir / "eks-addon-versions.json"
        with open(addon_versions_file, 'w') as f:
            json.dump(addon_versions_data, f, indent=2, default=str)
        
        click.echo(f"✅ EKS addon version data saved to shared location: {addon_versions_file}")
        return str(addon_versions_file)
    
    @staticmethod
    def load_addon_versions_data(output_dir: str) -> Optional[Dict[str, Any]]:
        """Load cached addon version data from shared parent directory."""
        output_path = Path(output_dir)
        
        # Determine the parent directory for shared addon data
        if output_path.parent.name == "assessment-reports":
            # We're in a timestamped assessment directory, go to parent
            shared_data_dir = output_path.parent / "shared-data"
        elif output_path.name.startswith("assessment-reports"):
            # We're in the assessment-reports directory itself
            shared_data_dir = output_path / "shared-data"
        else:
            # For custom output directories, create a shared-data subdirectory
            shared_data_dir = output_path / "shared-data"
        
        addon_versions_file = shared_data_dir / "eks-addon-versions.json"
        
        if addon_versions_file.exists():
            try:
                with open(addon_versions_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                click.echo(f"⚠️  Warning: Could not load cached addon versions data: {e}")
                return None
        return None


def fetch_and_cache_addon_versions(region: str, output_dir: str, force_refresh: bool = False) -> str:
    """Fetch and cache addon version data for the assessment."""
    
    # Check if cached data exists and is recent (unless force refresh)
    if not force_refresh:
        cached_data = EKSAddonVersionFetcher.load_addon_versions_data(output_dir)
        if cached_data:
            click.echo("✅ Using cached EKS addon version data from shared location")
            
            # Return the path to the shared data file
            output_path = Path(output_dir)
            if output_path.parent.name == "assessment-reports":
                shared_data_dir = output_path.parent / "shared-data"
            elif output_path.name.startswith("assessment-reports"):
                shared_data_dir = output_path / "shared-data"
            else:
                shared_data_dir = output_path / "shared-data"
            
            return str(shared_data_dir / "eks-addon-versions.json")
    
    # Fetch fresh data
    fetcher = EKSAddonVersionFetcher(region=region)
    return fetcher.save_addon_versions_data(output_dir)
