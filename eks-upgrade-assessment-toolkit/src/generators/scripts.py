"""
Script Generator

This module generates automation scripts for assessment and validation.
"""

import os
from pathlib import Path
from typing import Dict, List
from jinja2 import Environment, FileSystemLoader


class ScriptGenerator:
    """Generates automation scripts for EKS upgrade assessment."""
    
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            # Default to templates directory relative to this file
            current_dir = Path(__file__).parent
            template_dir = current_dir.parent.parent / "templates"
        
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir / "scripts")),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate_assessment_checks_script(self, assessment_data: Dict, output_path: str) -> bool:
        """
        Generate assessment validation script.
        
        Args:
            assessment_data: Assessment data to base checks on
            output_path: Path to save the script
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.env.get_template('assessment-checks.sh.j2')
            
            # Extract cluster information
            clusters = assessment_data.get('clusters', [])
            cluster_names = [cluster.get('cluster_name') for cluster in clusters]
            
            template_data = {
                'clusters': clusters,
                'cluster_names': cluster_names,
                'aws_region': assessment_data.get('config', {}).get('aws_configuration', {}).get('region', 'us-west-2'),
                'aws_profile': assessment_data.get('config', {}).get('aws_configuration', {}).get('credentials_profile', 'default')
            }
            
            content = template.render(**template_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Make script executable
            os.chmod(output_path, 0o755)
            
            return True
            
        except Exception as e:
            print(f"Error generating assessment checks script: {e}")
            return False
    
    def generate_deprecated_api_scanner_script(self, assessment_data: Dict, output_path: str) -> bool:
        """
        Generate deprecated API scanner script.
        
        Args:
            assessment_data: Assessment data
            output_path: Path to save the script
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.env.get_template('deprecated-api-scanner.sh.j2')
            
            clusters = assessment_data.get('clusters', [])
            
            template_data = {
                'clusters': clusters,
                'target_version': assessment_data.get('config', {}).get('upgrade_targets', {}).get('control_plane_target_version', '1.28'),
                'aws_region': assessment_data.get('config', {}).get('aws_configuration', {}).get('region', 'us-west-2'),
                'aws_profile': assessment_data.get('config', {}).get('aws_configuration', {}).get('credentials_profile', 'default')
            }
            
            content = template.render(**template_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Make script executable
            os.chmod(output_path, 0o755)
            
            return True
            
        except Exception as e:
            print(f"Error generating deprecated API scanner script: {e}")
            return False
    
    def generate_cluster_metadata_collector_script(self, assessment_data: Dict, output_path: str) -> bool:
        """
        Generate cluster metadata collection script.
        
        Args:
            assessment_data: Assessment data
            output_path: Path to save the script
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.env.get_template('cluster-metadata-collector.sh.j2')
            
            clusters = assessment_data.get('clusters', [])
            cluster_names = [cluster.get('cluster_name') for cluster in clusters]
            
            template_data = {
                'cluster_names': cluster_names,
                'aws_region': assessment_data.get('config', {}).get('aws_configuration', {}).get('region', 'us-west-2'),
                'aws_profile': assessment_data.get('config', {}).get('aws_configuration', {}).get('credentials_profile', 'default')
            }
            
            content = template.render(**template_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Make script executable
            os.chmod(output_path, 0o755)
            
            return True
            
        except Exception as e:
            print(f"Error generating cluster metadata collector script: {e}")
            return False
    
    def generate_upgrade_validation_script(self, assessment_data: Dict, output_path: str) -> bool:
        """
        Generate upgrade validation script.
        
        Args:
            assessment_data: Assessment data
            output_path: Path to save the script
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.env.get_template('upgrade-validation.sh.j2')
            
            clusters = assessment_data.get('clusters', [])
            
            # Extract validation checks based on assessment findings
            validation_checks = []
            
            for cluster in clusters:
                cluster_name = cluster.get('cluster_name')
                
                # Add checks based on findings
                if cluster.get('deprecated_apis', {}).get('combined_summary', {}).get('total_issues_found', 0) > 0:
                    validation_checks.append({
                        'cluster': cluster_name,
                        'check': 'deprecated_apis',
                        'description': 'Verify deprecated APIs have been updated'
                    })
                
                if cluster.get('workload_analysis', {}).get('pod_disruption_budgets', {}).get('potential_issues'):
                    validation_checks.append({
                        'cluster': cluster_name,
                        'check': 'pod_disruption_budgets',
                        'description': 'Verify PodDisruptionBudgets allow sufficient disruptions'
                    })
                
                if not cluster.get('compatibility', {}).get('compatible', True):
                    validation_checks.append({
                        'cluster': cluster_name,
                        'check': 'version_compatibility',
                        'description': 'Verify version compatibility issues are resolved'
                    })
            
            template_data = {
                'clusters': clusters,
                'validation_checks': validation_checks,
                'target_version': assessment_data.get('config', {}).get('upgrade_targets', {}).get('control_plane_target_version', '1.28'),
                'aws_region': assessment_data.get('config', {}).get('aws_configuration', {}).get('region', 'us-west-2'),
                'aws_profile': assessment_data.get('config', {}).get('aws_configuration', {}).get('credentials_profile', 'default')
            }
            
            content = template.render(**template_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Make script executable
            os.chmod(output_path, 0o755)
            
            return True
            
        except Exception as e:
            print(f"Error generating upgrade validation script: {e}")
            return False
    
    def generate_all_scripts(self, assessment_data: Dict, output_dir: str) -> Dict[str, bool]:
        """
        Generate all automation scripts.
        
        Args:
            assessment_data: Assessment data
            output_dir: Directory to save scripts
            
        Returns:
            Dictionary with script names and success status
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        # Generate assessment checks script
        results['assessment-checks.sh'] = self.generate_assessment_checks_script(
            assessment_data,
            str(output_path / 'assessment-checks.sh')
        )
        
        # Generate deprecated API scanner script
        results['deprecated-api-scanner.sh'] = self.generate_deprecated_api_scanner_script(
            assessment_data,
            str(output_path / 'deprecated-api-scanner.sh')
        )
        
        # Generate cluster metadata collector script
        results['cluster-metadata-collector.sh'] = self.generate_cluster_metadata_collector_script(
            assessment_data,
            str(output_path / 'cluster-metadata-collector.sh')
        )
        
        # Generate upgrade validation script
        results['upgrade-validation.sh'] = self.generate_upgrade_validation_script(
            assessment_data,
            str(output_path / 'upgrade-validation.sh')
        )
        
        return results
