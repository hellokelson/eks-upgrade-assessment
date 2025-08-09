"""
Workload Analyzer

This module analyzes workloads for upgrade readiness including PodDisruptionBudgets,
topology constraints, and other workload-specific considerations.
"""

from typing import Dict, List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException


class WorkloadAnalyzer:
    """Analyzes workloads for EKS upgrade readiness."""
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        self.kubeconfig_path = kubeconfig_path
        self._load_kubernetes_config()
    
    def _load_kubernetes_config(self):
        """Load Kubernetes configuration."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                config.load_kube_config()
            
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.policy_v1 = client.PolicyV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            
        except Exception as e:
            print(f"Failed to load Kubernetes config: {e}")
            self.v1 = None
            self.apps_v1 = None
            self.policy_v1 = None
            self.networking_v1 = None
    
    def analyze_pod_disruption_budgets(self, cluster_name: str) -> Dict:
        """
        Analyze PodDisruptionBudgets for upgrade impact.
        
        Args:
            cluster_name: Name of the EKS cluster
            
        Returns:
            Dictionary containing PDB analysis
        """
        if not self.policy_v1:
            return {
                'cluster_name': cluster_name,
                'error': 'Kubernetes client not available',
                'pdbs': []
            }
        
        try:
            pdbs = self.policy_v1.list_pod_disruption_budget_for_all_namespaces()
            
            analysis = {
                'cluster_name': cluster_name,
                'total_pdbs': len(pdbs.items),
                'pdbs': [],
                'potential_issues': [],
                'recommendations': []
            }
            
            for pdb in pdbs.items:
                pdb_info = {
                    'name': pdb.metadata.name,
                    'namespace': pdb.metadata.namespace,
                    'min_available': pdb.spec.min_available,
                    'max_unavailable': pdb.spec.max_unavailable,
                    'current_healthy': pdb.status.current_healthy if pdb.status else 0,
                    'desired_healthy': pdb.status.desired_healthy if pdb.status else 0,
                    'disruptions_allowed': pdb.status.disruptions_allowed if pdb.status else 0
                }
                
                analysis['pdbs'].append(pdb_info)
                
                # Check for potential issues
                if pdb_info['disruptions_allowed'] == 0:
                    analysis['potential_issues'].append({
                        'pdb': f"{pdb_info['namespace']}/{pdb_info['name']}",
                        'issue': 'No disruptions allowed - may block node upgrades',
                        'severity': 'high'
                    })
                
                if pdb_info['min_available'] and isinstance(pdb_info['min_available'], str):
                    if pdb_info['min_available'].endswith('%'):
                        percentage = int(pdb_info['min_available'].rstrip('%'))
                        if percentage > 80:
                            analysis['potential_issues'].append({
                                'pdb': f"{pdb_info['namespace']}/{pdb_info['name']}",
                                'issue': f'High min_available percentage ({percentage}%) may limit upgrade flexibility',
                                'severity': 'medium'
                            })
            
            # Add recommendations
            if analysis['potential_issues']:
                analysis['recommendations'].append(
                    'Review PodDisruptionBudgets before upgrade to ensure they allow sufficient disruptions'
                )
                analysis['recommendations'].append(
                    'Consider temporarily relaxing PDB constraints during upgrade window'
                )
            
            return analysis
            
        except ApiException as e:
            return {
                'cluster_name': cluster_name,
                'error': f'Kubernetes API error: {e}',
                'pdbs': []
            }
        except Exception as e:
            return {
                'cluster_name': cluster_name,
                'error': f'Unexpected error: {e}',
                'pdbs': []
            }
    
    def analyze_workload_distribution(self, cluster_name: str) -> Dict:
        """
        Analyze workload distribution across nodes and zones.
        
        Args:
            cluster_name: Name of the EKS cluster
            
        Returns:
            Dictionary containing workload distribution analysis
        """
        if not self.v1 or not self.apps_v1:
            return {
                'cluster_name': cluster_name,
                'error': 'Kubernetes client not available'
            }
        
        try:
            # Get all pods
            pods = self.v1.list_pod_for_all_namespaces()
            
            # Get all nodes
            nodes = self.v1.list_node()
            
            analysis = {
                'cluster_name': cluster_name,
                'total_pods': len(pods.items),
                'total_nodes': len(nodes.items),
                'node_distribution': {},
                'zone_distribution': {},
                'namespace_distribution': {},
                'workload_types': {},
                'potential_issues': [],
                'recommendations': []
            }
            
            # Analyze pod distribution
            for pod in pods.items:
                if pod.spec.node_name:
                    node_name = pod.spec.node_name
                    namespace = pod.metadata.namespace
                    
                    # Count by node
                    analysis['node_distribution'][node_name] = \
                        analysis['node_distribution'].get(node_name, 0) + 1
                    
                    # Count by namespace
                    analysis['namespace_distribution'][namespace] = \
                        analysis['namespace_distribution'].get(namespace, 0) + 1
                    
                    # Determine workload type
                    owner_refs = pod.metadata.owner_references or []
                    workload_type = 'standalone-pod'
                    
                    for owner in owner_refs:
                        if owner.kind in ['ReplicaSet', 'Deployment']:
                            workload_type = 'deployment'
                        elif owner.kind == 'DaemonSet':
                            workload_type = 'daemonset'
                        elif owner.kind == 'StatefulSet':
                            workload_type = 'statefulset'
                        elif owner.kind == 'Job':
                            workload_type = 'job'
                        break
                    
                    analysis['workload_types'][workload_type] = \
                        analysis['workload_types'].get(workload_type, 0) + 1
            
            # Analyze zone distribution
            for node in nodes.items:
                zone = node.metadata.labels.get('topology.kubernetes.io/zone', 'unknown')
                node_name = node.metadata.name
                pod_count = analysis['node_distribution'].get(node_name, 0)
                
                analysis['zone_distribution'][zone] = \
                    analysis['zone_distribution'].get(zone, 0) + pod_count
            
            # Check for potential issues
            self._check_distribution_issues(analysis)
            
            return analysis
            
        except ApiException as e:
            return {
                'cluster_name': cluster_name,
                'error': f'Kubernetes API error: {e}'
            }
        except Exception as e:
            return {
                'cluster_name': cluster_name,
                'error': f'Unexpected error: {e}'
            }
    
    def analyze_resource_constraints(self, cluster_name: str) -> Dict:
        """
        Analyze resource constraints that might affect upgrades.
        
        Args:
            cluster_name: Name of the EKS cluster
            
        Returns:
            Dictionary containing resource constraint analysis
        """
        if not self.v1:
            return {
                'cluster_name': cluster_name,
                'error': 'Kubernetes client not available'
            }
        
        try:
            # Get resource quotas
            quotas = self.v1.list_resource_quota_for_all_namespaces()
            
            # Get limit ranges
            limit_ranges = self.v1.list_limit_range_for_all_namespaces()
            
            analysis = {
                'cluster_name': cluster_name,
                'resource_quotas': [],
                'limit_ranges': [],
                'potential_constraints': [],
                'recommendations': []
            }
            
            # Analyze resource quotas
            for quota in quotas.items:
                quota_info = {
                    'name': quota.metadata.name,
                    'namespace': quota.metadata.namespace,
                    'hard_limits': dict(quota.spec.hard) if quota.spec.hard else {},
                    'used': dict(quota.status.used) if quota.status and quota.status.used else {}
                }
                
                analysis['resource_quotas'].append(quota_info)
                
                # Check for tight quotas
                if quota.status and quota.status.used and quota.spec.hard:
                    for resource, used_str in quota.status.used.items():
                        if resource in quota.spec.hard:
                            hard_limit_str = quota.spec.hard[resource]
                            
                            # Simple numeric comparison (could be enhanced for different units)
                            try:
                                used = int(used_str)
                                hard_limit = int(hard_limit_str)
                                
                                if used / hard_limit > 0.8:  # 80% threshold
                                    analysis['potential_constraints'].append({
                                        'type': 'resource_quota',
                                        'namespace': quota.metadata.namespace,
                                        'resource': resource,
                                        'usage_percentage': (used / hard_limit) * 100,
                                        'issue': f'High resource quota usage for {resource}'
                                    })
                            except ValueError:
                                # Skip non-numeric resources
                                pass
            
            # Analyze limit ranges
            for lr in limit_ranges.items:
                lr_info = {
                    'name': lr.metadata.name,
                    'namespace': lr.metadata.namespace,
                    'limits': []
                }
                
                if lr.spec.limits:
                    for limit in lr.spec.limits:
                        lr_info['limits'].append({
                            'type': limit.type,
                            'default': dict(limit.default) if limit.default else {},
                            'default_request': dict(limit.default_request) if limit.default_request else {},
                            'max': dict(limit.max) if limit.max else {},
                            'min': dict(limit.min) if limit.min else {}
                        })
                
                analysis['limit_ranges'].append(lr_info)
            
            # Add recommendations
            if analysis['potential_constraints']:
                analysis['recommendations'].append(
                    'Monitor resource usage during upgrade to avoid quota violations'
                )
                analysis['recommendations'].append(
                    'Consider temporarily increasing resource quotas during upgrade window'
                )
            
            return analysis
            
        except ApiException as e:
            return {
                'cluster_name': cluster_name,
                'error': f'Kubernetes API error: {e}'
            }
        except Exception as e:
            return {
                'cluster_name': cluster_name,
                'error': f'Unexpected error: {e}'
            }
    
    def comprehensive_workload_analysis(self, cluster_name: str) -> Dict:
        """
        Run comprehensive workload analysis.
        
        Args:
            cluster_name: Name of the EKS cluster
            
        Returns:
            Dictionary containing comprehensive workload analysis
        """
        pdb_analysis = self.analyze_pod_disruption_budgets(cluster_name)
        distribution_analysis = self.analyze_workload_distribution(cluster_name)
        constraint_analysis = self.analyze_resource_constraints(cluster_name)
        
        return {
            'cluster_name': cluster_name,
            'analysis_timestamp': self._get_timestamp(),
            'pod_disruption_budgets': pdb_analysis,
            'workload_distribution': distribution_analysis,
            'resource_constraints': constraint_analysis,
            'overall_recommendations': self._generate_overall_recommendations(
                pdb_analysis, distribution_analysis, constraint_analysis
            )
        }
    
    def _check_distribution_issues(self, analysis: Dict):
        """Check for workload distribution issues."""
        # Check for uneven node distribution
        if analysis['node_distribution']:
            pod_counts = list(analysis['node_distribution'].values())
            if pod_counts:
                avg_pods = sum(pod_counts) / len(pod_counts)
                max_pods = max(pod_counts)
                min_pods = min(pod_counts)
                
                if max_pods > avg_pods * 2:
                    analysis['potential_issues'].append({
                        'type': 'uneven_distribution',
                        'issue': 'Uneven pod distribution across nodes may cause upgrade issues',
                        'severity': 'medium'
                    })
        
        # Check for single points of failure
        if analysis['workload_types'].get('standalone-pod', 0) > 0:
            analysis['potential_issues'].append({
                'type': 'standalone_pods',
                'issue': 'Standalone pods detected - may not survive node upgrades',
                'severity': 'high'
            })
        
        # Add recommendations based on issues
        if analysis['potential_issues']:
            analysis['recommendations'].append(
                'Consider rebalancing workloads before upgrade'
            )
            analysis['recommendations'].append(
                'Ensure critical workloads have appropriate redundancy'
            )
    
    def _generate_overall_recommendations(self, pdb_analysis: Dict, 
                                       distribution_analysis: Dict, 
                                       constraint_analysis: Dict) -> List[str]:
        """Generate overall recommendations based on all analyses."""
        recommendations = []
        
        # Collect all individual recommendations
        for analysis in [pdb_analysis, distribution_analysis, constraint_analysis]:
            if 'recommendations' in analysis:
                recommendations.extend(analysis['recommendations'])
        
        # Add general recommendations
        recommendations.extend([
            'Test upgrade process in a staging environment first',
            'Plan upgrade during maintenance window with minimal traffic',
            'Monitor cluster health and workload availability during upgrade',
            'Have rollback plan ready in case of issues'
        ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
