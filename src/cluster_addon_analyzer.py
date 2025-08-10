"""
Cluster-Specific Addon Compatibility Analyzer
Analyzes individual cluster addons against the pre-fetched addon version data.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import click


class ClusterAddonCompatibilityAnalyzer:
    """Analyzes cluster addon compatibility using pre-fetched version data."""
    
    def __init__(self, addon_versions_data: Dict[str, Any]):
        self.addon_versions_data = addon_versions_data
        self.addon_versions_matrix = addon_versions_data.get('addon_versions', {})
    
    def analyze_cluster_addon_compatibility(self, cluster_name: str, current_eks_version: str, 
                                          target_eks_version: str, current_addons: List[Dict]) -> Dict[str, Any]:
        """Analyze addon compatibility for cluster upgrade to target version."""
        click.echo(f"    🔧 Analyzing addon compatibility: {current_eks_version} → {target_eks_version}")
        
        analysis_results = {
            'cluster_name': cluster_name,
            'current_eks_version': current_eks_version,
            'target_eks_version': target_eks_version,
            'addon_analysis': [],
            'summary': {
                'total_addons': len(current_addons),
                'pass': 0,
                'error': 0,
                'warning': 0,
                'unknown': 0
            },
            'upgrade_required': False,
            'blocking_issues': []
        }
        
        # Get target version addon requirements
        target_addon_requirements = self.addon_versions_matrix.get(target_eks_version, {})
        
        if not target_addon_requirements:
            click.echo(f"      ⚠️  No addon version data available for EKS {target_eks_version}")
            analysis_results['summary']['unknown'] = len(current_addons)
            return analysis_results
        
        for current_addon in current_addons:
            addon_name = current_addon.get('name', current_addon.get('addonName', ''))
            current_version = current_addon.get('version', current_addon.get('addonVersion', ''))
            
            addon_analysis = self._analyze_single_addon_compatibility(
                addon_name, current_version, target_addon_requirements
            )
            
            analysis_results['addon_analysis'].append(addon_analysis)
            
            # Update summary based on status
            status = addon_analysis['status']
            analysis_results['summary'][status] += 1
            
            # Check for upgrade requirements and blocking issues
            if status == 'error':
                analysis_results['blocking_issues'].append({
                    'addon_name': addon_name,
                    'issue': addon_analysis['message'],
                    'action_required': addon_analysis['action_required']
                })
            elif status in ['error', 'warning']:
                analysis_results['upgrade_required'] = True
        
        return analysis_results
    
    def _analyze_single_addon_compatibility(self, addon_name: str, current_version: str, 
                                          target_addon_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze compatibility for a single addon."""
        
        # Get target version requirements for this addon
        target_addon_info = target_addon_requirements.get(addon_name)
        
        if not target_addon_info:
            return {
                'addon_name': addon_name,
                'current_version': current_version,
                'status': 'unknown',
                'message': f'Addon {addon_name} not found in target EKS version requirements',
                'action_required': 'Manual verification required - addon may not be supported in target version',
                'target_requirements': None
            }
        
        # Extract target version requirements
        target_min = target_addon_info.get('min_addon_version')
        target_max = target_addon_info.get('max_addon_version')
        target_default = target_addon_info.get('default_version')
        addon_type = target_addon_info.get('addon_type', 'unknown')
        
        if not target_min or not target_max:
            return {
                'addon_name': addon_name,
                'current_version': current_version,
                'status': 'unknown',
                'message': 'Target version requirements not available',
                'action_required': 'Manual verification required',
                'target_requirements': {
                    'min_version': target_min,
                    'max_version': target_max,
                    'default_version': target_default,
                    'addon_type': addon_type
                }
            }
        
        # Determine compatibility status
        compatibility_result = self._determine_compatibility_status(
            current_version, target_min, target_max, target_default, addon_name
        )
        
        return {
            'addon_name': addon_name,
            'current_version': current_version,
            'status': compatibility_result['status'],
            'message': compatibility_result['message'],
            'action_required': compatibility_result['action_required'],
            'target_requirements': {
                'min_version': target_min,
                'max_version': target_max,
                'default_version': target_default,
                'addon_type': addon_type,
                'all_versions': target_addon_info.get('all_versions', [])
            }
        }
    
    def _determine_compatibility_status(self, current_version: str, target_min: str, 
                                      target_max: str, target_default: str, addon_name: str) -> Dict[str, str]:
        """Determine compatibility status and required actions."""
        try:
            # Compare versions
            if self._is_version_in_range(current_version, target_min, target_max):
                return {
                    'status': 'pass',
                    'message': f'Current version {current_version} is compatible with target EKS version',
                    'action_required': 'No action required - addon is compatible'
                }
            elif self._is_version_less_than(current_version, target_min):
                return {
                    'status': 'error',
                    'message': f'Current version {current_version} is below minimum required version {target_min}',
                    'action_required': f'UPGRADE REQUIRED: Update to version {target_default or target_min} or higher before EKS upgrade'
                }
            elif self._is_version_greater_than(current_version, target_max):
                return {
                    'status': 'warning',
                    'message': f'Current version {current_version} is above maximum supported version {target_max}',
                    'action_required': f'DOWNGRADE RECOMMENDED: Consider using version {target_default or target_max} for better compatibility'
                }
            else:
                return {
                    'status': 'warning',
                    'message': f'Version compatibility unclear between {current_version} and range {target_min}-{target_max}',
                    'action_required': f'VERIFICATION REQUIRED: Consider updating to recommended version {target_default}'
                }
        except Exception as e:
            return {
                'status': 'unknown',
                'message': f'Unable to compare versions: {str(e)}',
                'action_required': 'Manual verification required - version comparison failed'
            }
    
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
    
    def _is_version_greater_than(self, version1: str, version2: str) -> bool:
        """Check if version1 is greater than version2."""
        try:
            def parse_version(v):
                return [int(x) for x in v.lstrip('v').split('-')[0].split('.')]
            
            v1_parsed = parse_version(version1)
            v2_parsed = parse_version(version2)
            
            return v1_parsed > v2_parsed
        except Exception:
            return False


def analyze_cluster_addons(cluster_name: str, current_eks_version: str, target_eks_version: str,
                          current_addons: List[Dict], addon_versions_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze cluster addon compatibility using pre-fetched version data."""
    
    analyzer = ClusterAddonCompatibilityAnalyzer(addon_versions_data)
    return analyzer.analyze_cluster_addon_compatibility(
        cluster_name, current_eks_version, target_eks_version, current_addons
    )
