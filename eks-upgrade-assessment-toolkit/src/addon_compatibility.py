"""
EKS Addon Compatibility Analysis for Target Version Upgrades
Provides comprehensive addon version compatibility mapping across EKS versions.
"""

import json
import boto3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AddonVersionInfo:
    """Addon version information for a specific EKS version."""
    addon_name: str
    eks_version: str
    min_addon_version: str
    max_addon_version: str
    default_version: str
    addon_type: str  # 'core_aws', 'third_party', 'marketplace'
    compatibility_status: str  # 'compatible', 'upgrade_required', 'incompatible'


class EKSAddonCompatibilityAnalyzer:
    """Analyzes EKS addon compatibility for target version upgrades."""
    
    def __init__(self, region: str = 'us-west-2'):
        self.region = region
        self.eks_client = boto3.client('eks', region_name=region)
        self.compatibility_data = {}
        
    def fetch_addon_compatibility_data(self) -> Dict[str, Any]:
        """Fetch comprehensive addon compatibility data from AWS."""
        print("🔍 Fetching EKS addon compatibility data...")
        
        # Get all supported EKS versions
        eks_versions = self._get_supported_eks_versions()
        
        # Get all available addons
        available_addons = self._get_available_addons()
        
        compatibility_matrix = {}
        
        for eks_version in eks_versions:
            print(f"   📊 Analyzing EKS version {eks_version}...")
            compatibility_matrix[eks_version] = {}
            
            for addon_name in available_addons:
                try:
                    addon_info = self._get_addon_versions_for_eks_version(addon_name, eks_version)
                    if addon_info:
                        compatibility_matrix[eks_version][addon_name] = addon_info
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not get addon info for {addon_name} on EKS {eks_version}: {e}")
        
        return compatibility_matrix
    
    def _get_supported_eks_versions(self) -> List[str]:
        """Get list of supported EKS versions."""
        try:
            # Get EKS versions from describe-addon-versions for a common addon
            response = self.eks_client.describe_addon_versions(addonName='vpc-cni')
            versions = set()
            
            for addon_version in response.get('addons', []):
                for compatibility in addon_version.get('compatibilities', []):
                    versions.add(compatibility.get('clusterVersion'))
            
            # Sort versions
            sorted_versions = sorted(list(versions), key=lambda x: [int(i) for i in x.split('.')])
            return sorted_versions
            
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch EKS versions, using default list: {e}")
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
            print(f"⚠️  Warning: Could not fetch addon list: {e}")
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
            print(f"   ⚠️  Could not get versions for {addon_name} on EKS {eks_version}: {e}")
            return None
    
    def _determine_addon_type(self, addon_name: str) -> str:
        """Determine the type of addon."""
        core_aws_addons = {
            'vpc-cni', 'coredns', 'kube-proxy', 'aws-ebs-csi-driver', 
            'aws-efs-csi-driver', 'aws-fsx-csi-driver'
        }
        
        aws_addons = {
            'aws-load-balancer-controller', 'aws-for-fluent-bit', 
            'aws-cloudwatch-metrics', 'aws-node-termination-handler',
            'cluster-autoscaler', 'aws-distro-for-opentelemetry'
        }
        
        if addon_name in core_aws_addons:
            return 'core_aws'
        elif addon_name in aws_addons:
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
    
    def analyze_cluster_addon_compatibility(self, cluster_name: str, current_eks_version: str, 
                                          target_eks_version: str, current_addons: List[Dict]) -> Dict[str, Any]:
        """Analyze addon compatibility for cluster upgrade to target version."""
        print(f"🔍 Analyzing addon compatibility for {cluster_name}: {current_eks_version} → {target_eks_version}")
        
        # Load or fetch compatibility data
        compatibility_data = self.get_compatibility_data()
        
        analysis_results = {
            'cluster_name': cluster_name,
            'current_eks_version': current_eks_version,
            'target_eks_version': target_eks_version,
            'addon_analysis': [],
            'summary': {
                'total_addons': len(current_addons),
                'compatible': 0,
                'upgrade_required': 0,
                'incompatible': 0,
                'unknown': 0
            }
        }
        
        for current_addon in current_addons:
            addon_name = current_addon.get('name', current_addon.get('addonName', ''))
            current_version = current_addon.get('version', current_addon.get('addonVersion', ''))
            
            addon_analysis = self._analyze_single_addon_compatibility(
                addon_name, current_version, current_eks_version, target_eks_version, compatibility_data
            )
            
            analysis_results['addon_analysis'].append(addon_analysis)
            
            # Update summary
            status = addon_analysis['compatibility_status']
            analysis_results['summary'][status] += 1
        
        return analysis_results
    
    def _analyze_single_addon_compatibility(self, addon_name: str, current_version: str, 
                                          current_eks_version: str, target_eks_version: str,
                                          compatibility_data: Dict) -> Dict[str, Any]:
        """Analyze compatibility for a single addon."""
        
        # Get target version compatibility info
        target_addon_info = compatibility_data.get(target_eks_version, {}).get(addon_name)
        current_addon_info = compatibility_data.get(current_eks_version, {}).get(addon_name)
        
        if not target_addon_info:
            return {
                'addon_name': addon_name,
                'current_version': current_version,
                'current_eks_version': current_eks_version,
                'target_eks_version': target_eks_version,
                'compatibility_status': 'unknown',
                'recommended_action': 'Manual verification required - addon compatibility data not available',
                'target_min_version': None,
                'target_max_version': None,
                'addon_type': 'unknown'
            }
        
        # Determine compatibility status
        target_min = target_addon_info.get('min_addon_version')
        target_max = target_addon_info.get('max_addon_version')
        addon_type = target_addon_info.get('addon_type', 'unknown')
        
        compatibility_status, recommended_action = self._determine_compatibility_status(
            current_version, target_min, target_max, addon_name
        )
        
        return {
            'addon_name': addon_name,
            'current_version': current_version,
            'current_eks_version': current_eks_version,
            'target_eks_version': target_eks_version,
            'compatibility_status': compatibility_status,
            'recommended_action': recommended_action,
            'target_min_version': target_min,
            'target_max_version': target_max,
            'target_default_version': target_addon_info.get('default_version'),
            'addon_type': addon_type,
            'all_target_versions': target_addon_info.get('all_versions', [])
        }
    
    def _determine_compatibility_status(self, current_version: str, target_min: str, 
                                      target_max: str, addon_name: str) -> tuple:
        """Determine compatibility status and recommended action."""
        if not target_min or not target_max:
            return 'unknown', 'Unable to determine compatibility - version range not available'
        
        try:
            # Compare versions
            if self._is_version_in_range(current_version, target_min, target_max):
                return 'compatible', 'Current version is compatible with target EKS version'
            elif self._is_version_less_than(current_version, target_min):
                return 'upgrade_required', f'Upgrade required: minimum version {target_min} needed'
            else:
                return 'upgrade_required', f'Version update recommended: use version between {target_min} and {target_max}'
        except Exception:
            return 'unknown', 'Unable to compare versions - manual verification required'
    
    def _is_version_in_range(self, version: str, min_version: str, max_version: str) -> bool:
        """Check if version is within the specified range."""
        try:
            def parse_version(v):
                return [int(x) for x in v.lstrip('v').split('-')[0].split('.')]
            
            v_parsed = parse_version(version)
            min_parsed = parse_version(min_version)
            max_parsed = parse_version(max_version)
            
            return min_parsed <= v_parsed <= max_parsed
        except Exception:
            return False
    
    def _is_version_less_than(self, version1: str, version2: str) -> bool:
        """Check if version1 is less than version2."""
        try:
            def parse_version(v):
                return [int(x) for x in v.lstrip('v').split('-')[0].split('.')]
            
            v1_parsed = parse_version(version1)
            v2_parsed = parse_version(version2)
            
            return v1_parsed < v2_parsed
        except Exception:
            return False
    
    def get_compatibility_data(self) -> Dict[str, Any]:
        """Get compatibility data, fetching if not cached."""
        if not self.compatibility_data:
            self.compatibility_data = self.fetch_addon_compatibility_data()
        return self.compatibility_data
    
    def save_compatibility_data(self, output_path: str):
        """Save compatibility data to JSON file."""
        compatibility_data = self.get_compatibility_data()
        
        output_file = Path(output_path) / "eks-addon-compatibility.json"
        with open(output_file, 'w') as f:
            json.dump(compatibility_data, f, indent=2, default=str)
        
        print(f"✅ Addon compatibility data saved to: {output_file}")
        return output_file
