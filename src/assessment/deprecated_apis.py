"""
Deprecated API Scanner

This module integrates with kubent and pluto tools to scan for deprecated APIs.
"""

import subprocess
import json
import yaml
from typing import Dict, List, Optional
from pathlib import Path


class DeprecatedAPIScanner:
    """Scans for deprecated Kubernetes APIs using kubent and pluto."""
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        self.kubeconfig_path = kubeconfig_path
    
    def run_kubent_scan(self, cluster_name: str, target_version: str) -> Dict:
        """
        Run kubent scan for deprecated APIs.
        
        Args:
            cluster_name: Name of the EKS cluster
            target_version: Target Kubernetes version
            
        Returns:
            Dictionary containing kubent scan results
        """
        try:
            cmd = ['kubent', '--target-version', target_version, '--output', 'json']
            
            if self.kubeconfig_path:
                cmd.extend(['--kubeconfig', self.kubeconfig_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                try:
                    kubent_data = json.loads(result.stdout)
                    return {
                        'cluster_name': cluster_name,
                        'target_version': target_version,
                        'tool': 'kubent',
                        'status': 'success',
                        'deprecated_apis': kubent_data,
                        'summary': self._summarize_kubent_results(kubent_data)
                    }
                except json.JSONDecodeError:
                    return {
                        'cluster_name': cluster_name,
                        'target_version': target_version,
                        'tool': 'kubent',
                        'status': 'error',
                        'error': 'Failed to parse kubent output as JSON',
                        'raw_output': result.stdout
                    }
            else:
                return {
                    'cluster_name': cluster_name,
                    'target_version': target_version,
                    'tool': 'kubent',
                    'status': 'error',
                    'error': result.stderr,
                    'return_code': result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {
                'cluster_name': cluster_name,
                'target_version': target_version,
                'tool': 'kubent',
                'status': 'error',
                'error': 'kubent scan timed out after 300 seconds'
            }
        except FileNotFoundError:
            return {
                'cluster_name': cluster_name,
                'target_version': target_version,
                'tool': 'kubent',
                'status': 'error',
                'error': 'kubent tool not found. Please install kubent.'
            }
        except Exception as e:
            return {
                'cluster_name': cluster_name,
                'target_version': target_version,
                'tool': 'kubent',
                'status': 'error',
                'error': str(e)
            }
    
    def run_pluto_scan(self, cluster_name: str, target_version: str) -> Dict:
        """
        Run pluto scan for deprecated APIs.
        
        Args:
            cluster_name: Name of the EKS cluster
            target_version: Target Kubernetes version
            
        Returns:
            Dictionary containing pluto scan results
        """
        try:
            cmd = ['pluto', 'detect-all-in-cluster', '--target-versions', f'k8s={target_version}', '--output', 'json']
            
            if self.kubeconfig_path:
                cmd.extend(['--kubeconfig', self.kubeconfig_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                try:
                    pluto_data = json.loads(result.stdout)
                    return {
                        'cluster_name': cluster_name,
                        'target_version': target_version,
                        'tool': 'pluto',
                        'status': 'success',
                        'deprecated_apis': pluto_data,
                        'summary': self._summarize_pluto_results(pluto_data)
                    }
                except json.JSONDecodeError:
                    return {
                        'cluster_name': cluster_name,
                        'target_version': target_version,
                        'tool': 'pluto',
                        'status': 'error',
                        'error': 'Failed to parse pluto output as JSON',
                        'raw_output': result.stdout
                    }
            else:
                return {
                    'cluster_name': cluster_name,
                    'target_version': target_version,
                    'tool': 'pluto',
                    'status': 'error',
                    'error': result.stderr,
                    'return_code': result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {
                'cluster_name': cluster_name,
                'target_version': target_version,
                'tool': 'pluto',
                'status': 'error',
                'error': 'pluto scan timed out after 300 seconds'
            }
        except FileNotFoundError:
            return {
                'cluster_name': cluster_name,
                'target_version': target_version,
                'tool': 'pluto',
                'status': 'error',
                'error': 'pluto tool not found. Please install pluto.'
            }
        except Exception as e:
            return {
                'cluster_name': cluster_name,
                'target_version': target_version,
                'tool': 'pluto',
                'status': 'error',
                'error': str(e)
            }
    
    def comprehensive_scan(self, cluster_name: str, target_version: str) -> Dict:
        """
        Run comprehensive deprecated API scan using both tools.
        
        Args:
            cluster_name: Name of the EKS cluster
            target_version: Target Kubernetes version
            
        Returns:
            Dictionary containing comprehensive scan results
        """
        kubent_results = self.run_kubent_scan(cluster_name, target_version)
        pluto_results = self.run_pluto_scan(cluster_name, target_version)
        
        return {
            'cluster_name': cluster_name,
            'target_version': target_version,
            'scan_timestamp': self._get_timestamp(),
            'kubent_results': kubent_results,
            'pluto_results': pluto_results,
            'combined_summary': self._combine_results(kubent_results, pluto_results)
        }
    
    def _summarize_kubent_results(self, kubent_data: Dict) -> Dict:
        """Summarize kubent scan results."""
        summary = {
            'total_deprecated': 0,
            'by_api_version': {},
            'by_kind': {},
            'critical_count': 0
        }
        
        # Process kubent results structure
        if isinstance(kubent_data, list):
            for item in kubent_data:
                summary['total_deprecated'] += 1
                
                api_version = item.get('apiVersion', 'unknown')
                kind = item.get('kind', 'unknown')
                
                summary['by_api_version'][api_version] = summary['by_api_version'].get(api_version, 0) + 1
                summary['by_kind'][kind] = summary['by_kind'].get(kind, 0) + 1
                
                if item.get('deprecated', False):
                    summary['critical_count'] += 1
        
        return summary
    
    def _summarize_pluto_results(self, pluto_data: Dict) -> Dict:
        """Summarize pluto scan results."""
        summary = {
            'total_deprecated': 0,
            'by_api_version': {},
            'by_kind': {},
            'critical_count': 0
        }
        
        # Process pluto results structure
        items = pluto_data.get('items', [])
        for item in items:
            summary['total_deprecated'] += 1
            
            api_version = item.get('api-version', 'unknown')
            kind = item.get('kind', 'unknown')
            
            summary['by_api_version'][api_version] = summary['by_api_version'].get(api_version, 0) + 1
            summary['by_kind'][kind] = summary['by_kind'].get(kind, 0) + 1
            
            if item.get('deprecated', False):
                summary['critical_count'] += 1
        
        return summary
    
    def _combine_results(self, kubent_results: Dict, pluto_results: Dict) -> Dict:
        """Combine results from both tools."""
        combined = {
            'tools_status': {
                'kubent': kubent_results.get('status', 'unknown'),
                'pluto': pluto_results.get('status', 'unknown')
            },
            'total_issues_found': 0,
            'unique_api_versions': set(),
            'unique_kinds': set(),
            'recommendations': []
        }
        
        # Combine kubent results
        if kubent_results.get('status') == 'success':
            kubent_summary = kubent_results.get('summary', {})
            combined['total_issues_found'] += kubent_summary.get('total_deprecated', 0)
            combined['unique_api_versions'].update(kubent_summary.get('by_api_version', {}).keys())
            combined['unique_kinds'].update(kubent_summary.get('by_kind', {}).keys())
        
        # Combine pluto results
        if pluto_results.get('status') == 'success':
            pluto_summary = pluto_results.get('summary', {})
            combined['total_issues_found'] += pluto_summary.get('total_deprecated', 0)
            combined['unique_api_versions'].update(pluto_summary.get('by_api_version', {}).keys())
            combined['unique_kinds'].update(pluto_summary.get('by_kind', {}).keys())
        
        # Convert sets to lists for JSON serialization
        combined['unique_api_versions'] = list(combined['unique_api_versions'])
        combined['unique_kinds'] = list(combined['unique_kinds'])
        
        # Add recommendations based on findings
        if combined['total_issues_found'] > 0:
            combined['recommendations'].append(
                "Review and update deprecated API versions before upgrading"
            )
            combined['recommendations'].append(
                "Test workloads with target Kubernetes version in a staging environment"
            )
        
        return combined
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
