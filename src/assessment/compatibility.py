"""
Version Compatibility Checker

This module checks version compatibility for EKS upgrades.
"""

from typing import Dict, List, Tuple, Optional
from packaging import version


class CompatibilityChecker:
    """Checks version compatibility for EKS cluster upgrades."""
    
    # EKS supported versions and compatibility matrix
    EKS_SUPPORTED_VERSIONS = [
        "1.24", "1.25", "1.26", "1.27", "1.28", "1.29", "1.30"
    ]
    
    # Version compatibility rules
    COMPATIBILITY_RULES = {
        "control_plane_data_plane_skew": 2,  # Control plane can be max 2 versions ahead
        "node_group_skew": 2,  # Node groups can be max 2 versions behind control plane
        "addon_compatibility": {
            "vpc-cni": {
                "1.24": ["1.12.0", "1.13.0", "1.14.0"],
                "1.25": ["1.13.0", "1.14.0", "1.15.0"],
                "1.26": ["1.14.0", "1.15.0", "1.16.0"],
                "1.27": ["1.15.0", "1.16.0", "1.17.0"],
                "1.28": ["1.16.0", "1.17.0", "1.18.0"],
                "1.29": ["1.17.0", "1.18.0", "1.19.0"],
                "1.30": ["1.18.0", "1.19.0", "1.20.0"]
            },
            "coredns": {
                "1.24": ["1.9.3", "1.10.0"],
                "1.25": ["1.10.0", "1.10.1"],
                "1.26": ["1.10.1", "1.11.0"],
                "1.27": ["1.11.0", "1.11.1"],
                "1.28": ["1.11.1", "1.11.2"],
                "1.29": ["1.11.2", "1.11.3"],
                "1.30": ["1.11.3", "1.11.4"]
            },
            "kube-proxy": {
                "1.24": ["1.24.0", "1.24.1"],
                "1.25": ["1.25.0", "1.25.1"],
                "1.26": ["1.26.0", "1.26.1"],
                "1.27": ["1.27.0", "1.27.1"],
                "1.28": ["1.28.0", "1.28.1"],
                "1.29": ["1.29.0", "1.29.1"],
                "1.30": ["1.30.0", "1.30.1"]
            }
        }
    }
    
    def __init__(self):
        pass
    
    def check_version_compatibility(self, 
                                  current_control_plane: str,
                                  target_control_plane: str,
                                  current_data_plane: str,
                                  target_data_plane: str) -> Dict:
        """
        Check version compatibility for upgrade path.
        
        Args:
            current_control_plane: Current control plane version
            target_control_plane: Target control plane version
            current_data_plane: Current data plane version
            target_data_plane: Target data plane version
            
        Returns:
            Dictionary containing compatibility analysis
        """
        analysis = {
            'compatible': True,
            'issues': [],
            'warnings': [],
            'recommendations': [],
            'upgrade_path': []
        }
        
        # Validate versions are supported
        if target_control_plane not in self.EKS_SUPPORTED_VERSIONS:
            analysis['compatible'] = False
            analysis['issues'].append(
                f"Target control plane version {target_control_plane} is not supported by EKS"
            )
        
        if target_data_plane not in self.EKS_SUPPORTED_VERSIONS:
            analysis['compatible'] = False
            analysis['issues'].append(
                f"Target data plane version {target_data_plane} is not supported by EKS"
            )
        
        # Check upgrade path validity
        upgrade_path = self._calculate_upgrade_path(current_control_plane, target_control_plane)
        analysis['upgrade_path'] = upgrade_path
        
        if not upgrade_path:
            analysis['compatible'] = False
            analysis['issues'].append(
                f"No valid upgrade path from {current_control_plane} to {target_control_plane}"
            )
        
        # Check version skew policies
        skew_issues = self._check_version_skew(
            current_control_plane, target_control_plane,
            current_data_plane, target_data_plane
        )
        
        if skew_issues:
            analysis['issues'].extend(skew_issues)
            analysis['compatible'] = False
        
        # Add recommendations
        if len(upgrade_path) > 1:
            analysis['recommendations'].append(
                f"Multi-step upgrade required: {' -> '.join(upgrade_path)}"
            )
        
        if self._version_difference(current_control_plane, target_control_plane) > 1:
            analysis['warnings'].append(
                "Upgrading more than one minor version may require additional testing"
            )
        
        return analysis
    
    def check_addon_compatibility(self, k8s_version: str, addons: List[Dict]) -> Dict:
        """
        Check addon compatibility with Kubernetes version.
        
        Args:
            k8s_version: Kubernetes version
            addons: List of addon configurations
            
        Returns:
            Dictionary containing addon compatibility analysis
        """
        analysis = {
            'compatible_addons': [],
            'incompatible_addons': [],
            'upgrade_required': [],
            'recommendations': []
        }
        
        for addon in addons:
            addon_name = addon.get('addonName', '')
            addon_version = addon.get('addonVersion', '')
            
            compatibility = self._check_single_addon_compatibility(
                addon_name, addon_version, k8s_version
            )
            
            if compatibility['compatible']:
                analysis['compatible_addons'].append({
                    'name': addon_name,
                    'version': addon_version,
                    'status': 'compatible'
                })
            elif compatibility['upgrade_available']:
                analysis['upgrade_required'].append({
                    'name': addon_name,
                    'current_version': addon_version,
                    'recommended_version': compatibility['recommended_version'],
                    'reason': compatibility['reason']
                })
            else:
                analysis['incompatible_addons'].append({
                    'name': addon_name,
                    'version': addon_version,
                    'reason': compatibility['reason']
                })
        
        # Add recommendations
        if analysis['upgrade_required']:
            analysis['recommendations'].append(
                "Update addons to compatible versions before upgrading cluster"
            )
        
        if analysis['incompatible_addons']:
            analysis['recommendations'].append(
                "Remove or replace incompatible addons before upgrading"
            )
        
        return analysis
    
    def _calculate_upgrade_path(self, current: str, target: str) -> List[str]:
        """Calculate the upgrade path between versions."""
        try:
            current_idx = self.EKS_SUPPORTED_VERSIONS.index(current)
            target_idx = self.EKS_SUPPORTED_VERSIONS.index(target)
            
            if target_idx <= current_idx:
                return []  # No upgrade needed or downgrade not supported
            
            # Return the path including intermediate versions
            return self.EKS_SUPPORTED_VERSIONS[current_idx:target_idx + 1]
            
        except ValueError:
            return []  # Version not found in supported versions
    
    def _check_version_skew(self, current_cp: str, target_cp: str, 
                           current_dp: str, target_dp: str) -> List[str]:
        """Check version skew policies."""
        issues = []
        
        # Check control plane to data plane skew
        cp_dp_skew = self._version_difference(target_cp, target_dp)
        if cp_dp_skew > self.COMPATIBILITY_RULES["control_plane_data_plane_skew"]:
            issues.append(
                f"Control plane version {target_cp} is more than "
                f"{self.COMPATIBILITY_RULES['control_plane_data_plane_skew']} "
                f"versions ahead of data plane version {target_dp}"
            )
        
        return issues
    
    def _version_difference(self, version1: str, version2: str) -> int:
        """Calculate the difference between two versions."""
        try:
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            return abs(v1.minor - v2.minor)
        except Exception:
            return 0
    
    def _check_single_addon_compatibility(self, addon_name: str, 
                                        addon_version: str, 
                                        k8s_version: str) -> Dict:
        """Check compatibility of a single addon."""
        result = {
            'compatible': False,
            'upgrade_available': False,
            'recommended_version': None,
            'reason': ''
        }
        
        if addon_name not in self.COMPATIBILITY_RULES["addon_compatibility"]:
            result['compatible'] = True
            result['reason'] = 'Addon not in compatibility matrix - assuming compatible'
            return result
        
        compatible_versions = self.COMPATIBILITY_RULES["addon_compatibility"][addon_name].get(k8s_version, [])
        
        if not compatible_versions:
            result['reason'] = f'No compatible versions found for Kubernetes {k8s_version}'
            return result
        
        if addon_version in compatible_versions:
            result['compatible'] = True
            result['reason'] = 'Current version is compatible'
        else:
            # Check if upgrade is available
            latest_compatible = compatible_versions[-1]
            try:
                if version.parse(addon_version) < version.parse(latest_compatible):
                    result['upgrade_available'] = True
                    result['recommended_version'] = latest_compatible
                    result['reason'] = f'Upgrade available to {latest_compatible}'
                else:
                    result['reason'] = f'Current version {addon_version} is newer than recommended'
            except Exception:
                result['reason'] = f'Version comparison failed for {addon_version}'
        
        return result
    
    def generate_compatibility_matrix(self, clusters: List[Dict]) -> Dict:
        """Generate a compatibility matrix for multiple clusters."""
        matrix = {
            'clusters': [],
            'summary': {
                'total_clusters': len(clusters),
                'compatible_clusters': 0,
                'clusters_needing_attention': 0
            }
        }
        
        for cluster in clusters:
            cluster_analysis = self.check_version_compatibility(
                cluster.get('current_control_plane_version'),
                cluster.get('target_control_plane_version'),
                cluster.get('current_data_plane_version'),
                cluster.get('target_data_plane_version')
            )
            
            cluster_result = {
                'cluster_name': cluster.get('cluster_name'),
                'current_versions': {
                    'control_plane': cluster.get('current_control_plane_version'),
                    'data_plane': cluster.get('current_data_plane_version')
                },
                'target_versions': {
                    'control_plane': cluster.get('target_control_plane_version'),
                    'data_plane': cluster.get('target_data_plane_version')
                },
                'compatibility': cluster_analysis
            }
            
            matrix['clusters'].append(cluster_result)
            
            if cluster_analysis['compatible']:
                matrix['summary']['compatible_clusters'] += 1
            else:
                matrix['summary']['clusters_needing_attention'] += 1
        
        return matrix
