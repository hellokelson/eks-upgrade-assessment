"""AWS client wrapper for EKS operations."""

import boto3
import json
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EKSClusterInfo:
    """EKS cluster information."""
    name: str
    version: str
    status: str
    endpoint: str
    platform_version: str
    created_at: str
    arn: str
    role_arn: str
    vpc_config: Dict[str, Any]
    logging: Dict[str, Any]
    identity: Dict[str, Any]
    tags: Dict[str, str]


@dataclass
class NodeGroupInfo:
    """EKS node group information."""
    cluster_name: str
    nodegroup_name: str
    status: str
    capacity_type: str
    instance_types: List[str]
    ami_type: str
    node_role: str
    scaling_config: Dict[str, Any]
    version: str
    release_version: str


class AWSClient:
    """AWS client wrapper for EKS operations."""
    
    def __init__(self, region: str, profile: str = "default"):
        """Initialize AWS client."""
        self.region = region
        self.profile = profile
        self._session = None
        self._eks_client = None
        self._ec2_client = None
        self._iam_client = None
        self._logs_client = None
        self._sts_client = None
        
    @property
    def session(self) -> boto3.Session:
        """Get or create boto3 session."""
        if self._session is None:
            try:
                self._session = boto3.Session(profile_name=self.profile, region_name=self.region)
            except Exception as e:
                raise NoCredentialsError(f"Failed to create AWS session: {str(e)}")
        return self._session
    
    @property
    def eks_client(self):
        """Get EKS client."""
        if self._eks_client is None:
            self._eks_client = self.session.client('eks')
        return self._eks_client
    
    @property
    def ec2_client(self):
        """Get EC2 client."""
        if self._ec2_client is None:
            self._ec2_client = self.session.client('ec2')
        return self._ec2_client
    
    @property
    def iam_client(self):
        """Get IAM client."""
        if self._iam_client is None:
            self._iam_client = self.session.client('iam')
        return self._iam_client
    
    @property
    def logs_client(self):
        """Get CloudWatch Logs client."""
        if self._logs_client is None:
            self._logs_client = self.session.client('logs')
        return self._logs_client
    
    @property
    def sts_client(self):
        """Get STS client."""
        if self._sts_client is None:
            self._sts_client = self.session.client('sts')
        return self._sts_client
    
    def test_connection(self) -> bool:
        """Test AWS connection and permissions."""
        try:
            # Test basic EKS permissions
            self.eks_client.list_clusters()
            return True
        except (ClientError, NoCredentialsError) as e:
            print(f"AWS connection test failed: {str(e)}")
            return False
    
    def get_account_id(self) -> str:
        """Get AWS account ID."""
        try:
            response = self.sts_client.get_caller_identity()
            return response['Account']
        except ClientError as e:
            raise Exception(f"Failed to get AWS account ID: {str(e)}")
    
    def discover_clusters(self) -> List[str]:
        """Discover all EKS clusters in the region."""
        try:
            response = self.eks_client.list_clusters()
            return response.get('clusters', [])
        except ClientError as e:
            print(f"Failed to discover clusters: {str(e)}")
            return []
    
    def get_cluster_info(self, cluster_name: str) -> Optional[EKSClusterInfo]:
        """Get detailed information about an EKS cluster."""
        try:
            response = self.eks_client.describe_cluster(name=cluster_name)
            cluster_data = response['cluster']
            
            return EKSClusterInfo(
                name=cluster_data['name'],
                version=cluster_data['version'],
                status=cluster_data['status'],
                endpoint=cluster_data['endpoint'],
                platform_version=cluster_data['platformVersion'],
                created_at=cluster_data['createdAt'].isoformat(),
                arn=cluster_data['arn'],
                role_arn=cluster_data['roleArn'],
                vpc_config=cluster_data.get('resourcesVpcConfig', {}),
                logging=cluster_data.get('logging', {}),
                identity=cluster_data.get('identity', {}),
                tags=cluster_data.get('tags', {})
            )
        except ClientError as e:
            print(f"Failed to get cluster info for {cluster_name}: {str(e)}")
            return None
    
    def get_node_groups(self, cluster_name: str) -> List[NodeGroupInfo]:
        """Get node groups for a cluster."""
        try:
            # List node groups
            response = self.eks_client.list_nodegroups(clusterName=cluster_name)
            nodegroup_names = response.get('nodegroups', [])
            
            node_groups = []
            for ng_name in nodegroup_names:
                ng_info = self.get_node_group_info(cluster_name, ng_name)
                if ng_info:
                    node_groups.append(ng_info)
            
            return node_groups
        except ClientError as e:
            print(f"Failed to get node groups for {cluster_name}: {str(e)}")
            return []
    
    def get_node_group_info(self, cluster_name: str, nodegroup_name: str) -> Optional[NodeGroupInfo]:
        """Get detailed information about a node group."""
        try:
            response = self.eks_client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name
            )
            ng_data = response['nodegroup']
            
            return NodeGroupInfo(
                cluster_name=cluster_name,
                nodegroup_name=ng_data['nodegroupName'],
                status=ng_data['status'],
                capacity_type=ng_data.get('capacityType', 'ON_DEMAND'),
                instance_types=ng_data.get('instanceTypes', []),
                ami_type=ng_data.get('amiType', ''),
                node_role=ng_data.get('nodeRole', ''),
                scaling_config=ng_data.get('scalingConfig', {}),
                version=ng_data.get('version', ''),
                release_version=ng_data.get('releaseVersion', '')
            )
        except ClientError as e:
            print(f"Failed to get node group info for {nodegroup_name}: {str(e)}")
            return None
    
    def get_cluster_insights(self, cluster_name: str) -> List[Dict[str, Any]]:
        """Get EKS cluster insights with detailed information for non-passing insights."""
        try:
            # Check if the client has the list_insights method
            if not hasattr(self.eks_client, 'list_insights'):
                print(f"Warning: EKS Insights API not available in this AWS SDK version for cluster {cluster_name}")
                return []
            
            response = self.eks_client.list_insights(
                clusterName=cluster_name
            )
            insights = response.get('insights', [])
            
            # For each non-passing insight, fetch detailed information
            enhanced_insights = []
            for insight in insights:
                insight_status = insight.get('insightStatus', {}).get('status', '')
                
                # If insight is not passing, fetch detailed information
                if insight_status != 'PASSING':
                    try:
                        insight_id = insight.get('id')
                        if insight_id:
                            detailed_response = self.eks_client.describe_insight(
                                clusterName=cluster_name,
                                id=insight_id
                            )
                            detailed_insight = detailed_response.get('insight', {})
                            
                            # Add the detailed insight information to the original insight
                            insight['insight'] = detailed_insight
                            
                    except ClientError as e:
                        print(f"Failed to get detailed insight {insight.get('id', 'unknown')} for {cluster_name}: {str(e)}")
                        # Continue without detailed info if describe_insight fails
                    except Exception as e:
                        print(f"Warning: Could not retrieve insight details: {str(e)}")
                        # Continue without detailed info
                
                enhanced_insights.append(insight)
            
            return enhanced_insights
            
        except ClientError as e:
            error_msg = str(e)
            if 'list_insights' in error_msg or 'describe_insight' in error_msg:
                print(f"Warning: EKS Insights API not available in region {self.eks_client.meta.region_name} for cluster {cluster_name}: {error_msg}")
            else:
                print(f"Failed to get cluster insights for {cluster_name}: {error_msg}")
            return []
        except Exception as e:
            print(f"Warning: Could not retrieve cluster insights for {cluster_name}: {str(e)}")
            return []
    
    def get_insight_details(self, cluster_name: str, insight_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific insight."""
        try:
            response = self.eks_client.describe_insight(
                clusterName=cluster_name,
                id=insight_id
            )
            return response.get('insight', {})
        except ClientError as e:
            print(f"Failed to get insight details for {insight_id}: {str(e)}")
            return None
    
    def get_addons(self, cluster_name: str) -> List[Dict[str, Any]]:
        """Get EKS addons for a cluster."""
        try:
            response = self.eks_client.list_addons(clusterName=cluster_name)
            addon_names = response.get('addons', [])
            
            addons = []
            for addon_name in addon_names:
                addon_info = self.get_addon_info(cluster_name, addon_name)
                if addon_info:
                    addons.append(addon_info)
            
            return addons
        except ClientError as e:
            print(f"Failed to get addons for {cluster_name}: {str(e)}")
            return []
    
    def get_addon_info(self, cluster_name: str, addon_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an addon."""
        try:
            response = self.eks_client.describe_addon(
                clusterName=cluster_name,
                addonName=addon_name
            )
            return response.get('addon', {})
        except ClientError as e:
            print(f"Failed to get addon info for {addon_name}: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error getting addon info for {addon_name}: {str(e)}")
            return None
    
    def get_fargate_profiles(self, cluster_name: str) -> List[Dict[str, Any]]:
        """Get Fargate profiles for a cluster."""
        try:
            response = self.eks_client.list_fargate_profiles(clusterName=cluster_name)
            profile_names = response.get('fargateProfileNames', [])
            
            profiles = []
            for profile_name in profile_names:
                profile_info = self.get_fargate_profile_info(cluster_name, profile_name)
                if profile_info:
                    profiles.append(profile_info)
            
            return profiles
        except ClientError as e:
            print(f"Failed to get Fargate profiles for {cluster_name}: {str(e)}")
            return []
    
    def get_fargate_profile_info(self, cluster_name: str, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Fargate profile."""
        try:
            response = self.eks_client.describe_fargate_profile(
                clusterName=cluster_name,
                fargateProfileName=profile_name
            )
            return response.get('fargateProfile', {})
        except ClientError as e:
            print(f"Failed to get Fargate profile info for {profile_name}: {str(e)}")
            return None
    
    def get_cluster_metadata(self, cluster_name: str, output_dir: str = None) -> Dict[str, Any]:
        """Get EKS upgrade-focused cluster metadata and save original data to separate files."""
        # EKS upgrade-focused metadata only
        metadata = {
            'cluster_name': cluster_name,
            'cluster_version': None,
            'cluster_status': None,
            'platform_version': None,
            'created_at': None,
            'node_groups': [],
            'fargate_profiles': [],
            'addons': [],
            'karpenter': {
                'installed': False,
                'node_pools_count': 0,
                'provisioners_count': 0
            }
            # Removed aws_plugins - plugin information is available in addons section
        }
        
        # Create cluster-specific directory structure for original data
        if output_dir:
            cluster_dir = Path(output_dir) / "cluster-metadata" / cluster_name
            cluster_dir.mkdir(parents=True, exist_ok=True)
            
            # Create categorized subdirectories
            (cluster_dir / "cluster").mkdir(exist_ok=True)
            (cluster_dir / "nodegroups").mkdir(exist_ok=True)
            (cluster_dir / "fargate").mkdir(exist_ok=True)
            (cluster_dir / "addons").mkdir(exist_ok=True)
            (cluster_dir / "karpenter").mkdir(exist_ok=True)
            (cluster_dir / "plugins").mkdir(exist_ok=True)
        
        try:
            print(f"    📊 Collecting basic cluster info...")
            # Get basic cluster information
            cluster_info = self.get_cluster_info(cluster_name)
            if cluster_info:
                metadata['cluster_version'] = cluster_info.version
                metadata['cluster_status'] = cluster_info.status
                metadata['platform_version'] = cluster_info.platform_version
                metadata['created_at'] = cluster_info.created_at
                
                # Save original cluster data to YAML file
                if output_dir:
                    cluster_data = {
                        'apiVersion': 'eks.aws.amazon.com/v1',
                        'kind': 'Cluster',
                        'metadata': {
                            'name': cluster_info.name,
                            'arn': cluster_info.arn,
                            'tags': cluster_info.tags
                        },
                        'spec': {
                            'version': cluster_info.version,
                            'platformVersion': cluster_info.platform_version,
                            'status': cluster_info.status,
                            'endpoint': cluster_info.endpoint,
                            'roleArn': cluster_info.role_arn,
                            'vpcConfig': cluster_info.vpc_config,
                            'logging': cluster_info.logging,
                            'identity': cluster_info.identity,
                            'createdAt': cluster_info.created_at
                        }
                    }
                    self._save_yaml_file(cluster_dir / "cluster" / "cluster.yaml", cluster_data)
            
            print(f"    📊 Collecting node groups...")
            # Get node groups - upgrade-focused info only
            try:
                node_groups = self.get_node_groups(cluster_name)
                for ng in node_groups:
                    metadata['node_groups'].append({
                        'name': ng.nodegroup_name,
                        'status': ng.status,
                        'version': ng.version,
                        'capacity_type': ng.capacity_type,
                        'instance_types': ng.instance_types,
                        'ami_type': ng.ami_type,
                        'node_role': ng.node_role,
                        'is_managed': True  # All node groups retrieved via EKS API are managed
                    })
                    
                    # Save original node group data
                    if output_dir:
                        ng_data = {
                            'apiVersion': 'eks.aws.amazon.com/v1',
                            'kind': 'NodeGroup',
                            'metadata': {
                                'name': ng.nodegroup_name,
                                'clusterName': ng.cluster_name
                            },
                            'spec': {
                                'status': ng.status,
                                'capacityType': ng.capacity_type,
                                'instanceTypes': ng.instance_types,
                                'amiType': ng.ami_type,
                                'nodeRole': ng.node_role,
                                'scalingConfig': ng.scaling_config,
                                'version': ng.version,
                                'releaseVersion': ng.release_version
                            }
                        }
                        self._save_yaml_file(cluster_dir / "nodegroups" / f"nodegroup-{ng.nodegroup_name}.yaml", ng_data)
            except Exception as e:
                print(f"    ⚠️  Error collecting node groups: {str(e)}")
            
            print(f"    📊 Collecting Fargate profiles...")
            # Get Fargate profiles - upgrade-focused info only
            try:
                fargate_profiles = self.get_fargate_profiles(cluster_name)
                for fp in fargate_profiles:
                    metadata['fargate_profiles'].append({
                        'name': fp.get('fargateProfileName'),
                        'status': fp.get('status')
                    })
                    
                    # Save original Fargate profile data
                    if output_dir:
                        fp_data = {
                            'apiVersion': 'eks.aws.amazon.com/v1',
                            'kind': 'FargateProfile',
                            'metadata': {
                                'name': fp.get('fargateProfileName'),
                                'clusterName': cluster_name
                            },
                            'spec': fp
                        }
                        self._save_yaml_file(cluster_dir / "fargate" / f"fargate-{fp.get('fargateProfileName')}.yaml", fp_data)
            except Exception as e:
                print(f"    ⚠️  Error collecting Fargate profiles: {str(e)}")
            
            print(f"    📊 Collecting EKS addons...")
            # Get addons - upgrade-focused info only
            try:
                addons = self.get_addons(cluster_name)
                for addon in addons:
                    metadata['addons'].append({
                        'name': addon.get('addonName'),
                        'version': addon.get('addonVersion'),
                        'status': addon.get('status')
                    })
                    
                    # Save original addon data
                    if output_dir:
                        addon_data = {
                            'apiVersion': 'eks.aws.amazon.com/v1',
                            'kind': 'Addon',
                            'metadata': {
                                'name': addon.get('addonName'),
                                'clusterName': cluster_name
                            },
                            'spec': addon
                        }
                        self._save_yaml_file(cluster_dir / "addons" / f"addon-{addon.get('addonName')}.yaml", addon_data)
            except Exception as e:
                print(f"    ⚠️  Error collecting addons: {str(e)}")
            
            print(f"    📊 Collecting Karpenter info...")
            # Get Karpenter information - upgrade-focused info only
            try:
                karpenter_info = self._get_karpenter_info_lightweight(cluster_name, cluster_dir if output_dir else None)
                metadata['karpenter'] = karpenter_info
            except Exception as e:
                print(f"    ⚠️  Error collecting Karpenter info: {str(e)}")
            
            # AWS plugins info is now available in the addons section - no separate collection needed
            
        except Exception as e:
            print(f"Error collecting metadata for {cluster_name}: {str(e)}")
            metadata['error'] = str(e)
        
        return metadata
    
    def _save_yaml_file(self, file_path: Path, data: Dict[str, Any]):
        """Save data to YAML file."""
        try:
            import yaml
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except ImportError:
            # Fallback to JSON if PyYAML not available
            import json
            with open(file_path.with_suffix('.json'), 'w') as f:
                json.dump(data, f, indent=2, default=str)
    
    def _get_karpenter_info_lightweight(self, cluster_name: str, cluster_dir: Path = None) -> Dict[str, Any]:
        """Get lightweight Karpenter information for upgrade purposes."""
        karpenter_info = {
            'installed': False,
            'node_pools_count': 0,
            'provisioners_count': 0,
            'version': None
        }
        
        try:
            import subprocess
            
            # Check for Karpenter NodePools
            result = subprocess.run(
                ['kubectl', 'get', 'nodepools', '-o', 'json'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                nodepools_data = json.loads(result.stdout)
                node_pools = nodepools_data.get('items', [])
                karpenter_info['node_pools_count'] = len(node_pools)
                if node_pools:
                    karpenter_info['installed'] = True
                    
                    # Save original NodePools data
                    if cluster_dir:
                        self._save_yaml_file(cluster_dir / "karpenter" / "karpenter-nodepools.yaml", nodepools_data)
            
            # Check for legacy Karpenter Provisioners
            result = subprocess.run(
                ['kubectl', 'get', 'provisioners', '-o', 'json'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                provisioners_data = json.loads(result.stdout)
                provisioners = provisioners_data.get('items', [])
                karpenter_info['provisioners_count'] = len(provisioners)
                if provisioners:
                    karpenter_info['installed'] = True
                    
                    # Save original Provisioners data
                    if cluster_dir:
                        self._save_yaml_file(cluster_dir / "karpenter" / "karpenter-provisioners.yaml", provisioners_data)
            
            # Check for Karpenter NodeClasses
            result = subprocess.run(
                ['kubectl', 'get', 'ec2nodeclasses', '-o', 'json'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                nodeclasses_data = json.loads(result.stdout)
                if nodeclasses_data.get('items') and cluster_dir:
                    self._save_yaml_file(cluster_dir / "karpenter" / "karpenter-nodeclasses.yaml", nodeclasses_data)
                    
        except Exception:
            # kubectl not configured or Karpenter not installed
            pass
        
        return karpenter_info
    
    def _get_aws_plugins_info_lightweight(self, cluster_name: str) -> Dict[str, Any]:
        """Get detailed AWS plugin information for upgrade purposes."""
        plugins_info = {
            'installed_plugins': []  # List of installed plugins with details
        }
        
        try:
            # Check EKS addons first
            addons = self.get_addons(cluster_name)
            addon_plugins = {
                'aws-load-balancer-controller': 'AWS Load Balancer Controller',
                'aws-ebs-csi-driver': 'EBS CSI Driver',
                'aws-efs-csi-driver': 'EFS CSI Driver',
                'cluster-autoscaler': 'Cluster Autoscaler'
            }
            
            for addon in addons:
                addon_name = addon.get('addonName')
                if addon_name in addon_plugins:
                    plugins_info['installed_plugins'].append({
                        'name': addon_plugins[addon_name],
                        'type': 'EKS Addon',
                        'version': addon.get('addonVersion', 'N/A'),
                        'status': addon.get('status', 'N/A'),
                        'namespace': 'kube-system'
                    })
            
            # Check for manually installed controllers via kubectl
            try:
                import subprocess
                
                manual_controllers = [
                    {
                        'name': 'AWS Load Balancer Controller',
                        'deployment': 'aws-load-balancer-controller',
                        'namespace': 'kube-system'
                    },
                    {
                        'name': 'Cluster Autoscaler',
                        'deployment': 'cluster-autoscaler',
                        'namespace': 'kube-system'
                    },
                    {
                        'name': 'External DNS',
                        'deployment': 'external-dns',
                        'namespace': 'kube-system'
                    },
                    {
                        'name': 'Cert Manager',
                        'deployment': 'cert-manager',
                        'namespace': 'cert-manager'
                    },
                    {
                        'name': 'Ingress NGINX',
                        'deployment': 'ingress-nginx-controller',
                        'namespace': 'ingress-nginx'
                    }
                ]
                
                # Check if already found via addons to avoid duplicates
                existing_plugins = [p['name'] for p in plugins_info['installed_plugins']]
                
                for controller in manual_controllers:
                    if controller['name'] not in existing_plugins:
                        result = subprocess.run(
                            ['kubectl', 'get', 'deployment', controller['deployment'], '-n', controller['namespace'], '-o', 'json'],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            try:
                                deployment_data = json.loads(result.stdout)
                                version = self._extract_image_version(deployment_data)
                                status = 'Available' if deployment_data.get('status', {}).get('readyReplicas', 0) > 0 else 'Unavailable'
                                
                                plugins_info['installed_plugins'].append({
                                    'name': controller['name'],
                                    'type': 'Manual Deployment',
                                    'version': version,
                                    'status': status,
                                    'namespace': controller['namespace']
                                })
                            except json.JSONDecodeError:
                                plugins_info['installed_plugins'].append({
                                    'name': controller['name'],
                                    'type': 'Manual Deployment',
                                    'version': 'Unknown',
                                    'status': 'Found',
                                    'namespace': controller['namespace']
                                })
                
                # Check for other common controllers in all namespaces
                common_controllers = ['prometheus-operator', 'grafana', 'fluent-bit', 'metrics-server']
                for controller in common_controllers:
                    if controller not in existing_plugins:
                        result = subprocess.run(
                            ['kubectl', 'get', 'deployment', controller, '--all-namespaces', '-o', 'json'],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            try:
                                deployment_data = json.loads(result.stdout)
                                if deployment_data.get('items'):
                                    for item in deployment_data['items']:
                                        version = self._extract_image_version(item)
                                        namespace = item.get('metadata', {}).get('namespace', 'unknown')
                                        status = 'Available' if item.get('status', {}).get('readyReplicas', 0) > 0 else 'Unavailable'
                                        
                                        plugins_info['installed_plugins'].append({
                                            'name': controller.replace('-', ' ').title(),
                                            'type': 'Third-party',
                                            'version': version,
                                            'status': status,
                                            'namespace': namespace
                                        })
                                        break  # Only add the first instance found
                            except json.JSONDecodeError:
                                pass
                    
            except Exception as e:
                print(f"    ⚠️  Error checking manual controllers: {str(e)}")
                
        except Exception as e:
            print(f"    ⚠️  Error collecting AWS plugins: {str(e)}")
            plugins_info['error'] = str(e)
        
        return plugins_info
    
    def _get_karpenter_info(self, cluster_name: str) -> Dict[str, Any]:
        """Get Karpenter-related information."""
        karpenter_info = {
            'installed': False,
            'version': None,
            'node_pools': [],
            'provisioners': [],
            'node_classes': [],
            'error': None
        }
        
        try:
            import subprocess
            
            # Check if Karpenter is installed via addon
            addons = self.get_addons(cluster_name)
            for addon in addons:
                if addon.get('addonName') == 'eks-pod-identity-agent' or 'karpenter' in addon.get('addonName', '').lower():
                    karpenter_info['installed'] = True
                    karpenter_info['version'] = addon.get('addonVersion')
            
            # Try to get Karpenter resources via kubectl (if configured)
            try:
                # Check for Karpenter NodePools
                result = subprocess.run(
                    ['kubectl', 'get', 'nodepools', '-o', 'json'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    nodepools_data = json.loads(result.stdout)
                    for item in nodepools_data.get('items', []):
                        karpenter_info['node_pools'].append({
                            'name': item.get('metadata', {}).get('name'),
                            'status': item.get('status', {}),
                            'spec': item.get('spec', {})
                        })
                
                # Check for legacy Karpenter Provisioners
                result = subprocess.run(
                    ['kubectl', 'get', 'provisioners', '-o', 'json'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    provisioners_data = json.loads(result.stdout)
                    for item in provisioners_data.get('items', []):
                        karpenter_info['provisioners'].append({
                            'name': item.get('metadata', {}).get('name'),
                            'status': item.get('status', {}),
                            'spec': item.get('spec', {})
                        })
                
                # Check for Karpenter NodeClasses
                result = subprocess.run(
                    ['kubectl', 'get', 'ec2nodeclasses', '-o', 'json'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    nodeclasses_data = json.loads(result.stdout)
                    for item in nodeclasses_data.get('items', []):
                        karpenter_info['node_classes'].append({
                            'name': item.get('metadata', {}).get('name'),
                            'status': item.get('status', {}),
                            'spec': item.get('spec', {})
                        })
                
                if karpenter_info['node_pools'] or karpenter_info['provisioners']:
                    karpenter_info['installed'] = True
                    
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError):
                # kubectl not configured or Karpenter not installed
                pass
                
        except Exception as e:
            karpenter_info['error'] = str(e)
        
        return karpenter_info
    
    def _get_aws_plugins_info(self, cluster_name: str) -> Dict[str, Any]:
        """Get AWS plugin and controller information."""
        plugins_info = {
            'aws_load_balancer_controller': {},
            'aws_ebs_csi_driver': {},
            'aws_efs_csi_driver': {},
            'aws_fsx_csi_driver': {},
            'cluster_autoscaler': {},
            'vpc_cni': {},
            'coredns': {},
            'kube_proxy': {},
            'other_controllers': [],
            'error': None
        }
        
        try:
            # Get information from EKS addons
            addons = self.get_addons(cluster_name)
            addon_map = {
                'aws-load-balancer-controller': 'aws_load_balancer_controller',
                'aws-ebs-csi-driver': 'aws_ebs_csi_driver',
                'aws-efs-csi-driver': 'aws_efs_csi_driver',
                'aws-fsx-csi-driver': 'aws_fsx_csi_driver',
                'cluster-autoscaler': 'cluster_autoscaler',
                'vpc-cni': 'vpc_cni',
                'coredns': 'coredns',
                'kube-proxy': 'kube_proxy'
            }
            
            for addon in addons:
                addon_name = addon.get('addonName')
                if addon_name in addon_map:
                    plugins_info[addon_map[addon_name]] = {
                        'installed_via': 'eks_addon',
                        'version': addon.get('addonVersion'),
                        'status': addon.get('status'),
                        'service_account_role_arn': addon.get('serviceAccountRoleArn'),
                        'configuration': addon.get('configurationValues')
                    }
            
            # Try to get additional controller information via kubectl
            try:
                import subprocess
                
                # Check for AWS Load Balancer Controller
                if not plugins_info['aws_load_balancer_controller']:
                    result = subprocess.run(
                        ['kubectl', 'get', 'deployment', 'aws-load-balancer-controller', '-n', 'kube-system', '-o', 'json'],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        deployment_data = json.loads(result.stdout)
                        plugins_info['aws_load_balancer_controller'] = {
                            'installed_via': 'manual_deployment',
                            'version': self._extract_image_version(deployment_data),
                            'status': deployment_data.get('status', {}),
                            'replicas': deployment_data.get('spec', {}).get('replicas')
                        }
                
                # Check for Cluster Autoscaler
                if not plugins_info['cluster_autoscaler']:
                    result = subprocess.run(
                        ['kubectl', 'get', 'deployment', 'cluster-autoscaler', '-n', 'kube-system', '-o', 'json'],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        deployment_data = json.loads(result.stdout)
                        plugins_info['cluster_autoscaler'] = {
                            'installed_via': 'manual_deployment',
                            'version': self._extract_image_version(deployment_data),
                            'status': deployment_data.get('status', {}),
                            'replicas': deployment_data.get('spec', {}).get('replicas')
                        }
                
                # Check for other common controllers
                common_controllers = [
                    'external-dns', 'cert-manager', 'ingress-nginx', 
                    'metrics-server', 'prometheus-operator'
                ]
                
                for controller in common_controllers:
                    result = subprocess.run(
                        ['kubectl', 'get', 'deployment', controller, '--all-namespaces', '-o', 'json'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        deployment_data = json.loads(result.stdout)
                        if deployment_data.get('items'):
                            for item in deployment_data['items']:
                                plugins_info['other_controllers'].append({
                                    'name': controller,
                                    'namespace': item.get('metadata', {}).get('namespace'),
                                    'version': self._extract_image_version(item),
                                    'status': item.get('status', {}),
                                    'replicas': item.get('spec', {}).get('replicas')
                                })
                
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError):
                # kubectl not configured or controllers not found
                pass
                
        except Exception as e:
            plugins_info['error'] = str(e)
        
        return plugins_info
    
    def _get_monitoring_info(self, cluster_name: str) -> Dict[str, Any]:
        """Get monitoring and observability information."""
        monitoring_info = {
            'cloudwatch_container_insights': False,
            'prometheus': {},
            'grafana': {},
            'jaeger': {},
            'x_ray': {},
            'fluent_bit': {},
            'error': None
        }
        
        try:
            # Check CloudWatch Container Insights
            try:
                response = self.logs_client.describe_log_groups(
                    logGroupNamePrefix=f'/aws/containerinsights/{cluster_name}'
                )
                if response.get('logGroups'):
                    monitoring_info['cloudwatch_container_insights'] = True
            except ClientError:
                pass
            
            # Try to check for monitoring tools via kubectl
            try:
                import subprocess
                
                # Check for Prometheus
                result = subprocess.run(
                    ['kubectl', 'get', 'deployment', '--all-namespaces', '-l', 'app.kubernetes.io/name=prometheus', '-o', 'json'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    prometheus_data = json.loads(result.stdout)
                    if prometheus_data.get('items'):
                        monitoring_info['prometheus'] = {
                            'installed': True,
                            'deployments': len(prometheus_data['items']),
                            'namespaces': list(set(item.get('metadata', {}).get('namespace') for item in prometheus_data['items']))
                        }
                
                # Check for Grafana
                result = subprocess.run(
                    ['kubectl', 'get', 'deployment', '--all-namespaces', '-l', 'app.kubernetes.io/name=grafana', '-o', 'json'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    grafana_data = json.loads(result.stdout)
                    if grafana_data.get('items'):
                        monitoring_info['grafana'] = {
                            'installed': True,
                            'deployments': len(grafana_data['items']),
                            'namespaces': list(set(item.get('metadata', {}).get('namespace') for item in grafana_data['items']))
                        }
                
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError):
                pass
                
        except Exception as e:
            monitoring_info['error'] = str(e)
        
        return monitoring_info
    
    def _extract_image_version(self, deployment_data: Dict[str, Any]) -> str:
        """Extract version from deployment image."""
        try:
            containers = deployment_data.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
            if containers:
                image = containers[0].get('image', '')
                if ':' in image:
                    return image.split(':')[-1]
            return 'unknown'
        except Exception:
            return 'unknown'