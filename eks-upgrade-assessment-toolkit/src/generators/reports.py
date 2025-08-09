"""
Report Generator

This module generates assessment reports in various formats.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader, Template


class ReportGenerator:
    """Generates assessment reports in multiple formats."""
    
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            # Default to templates directory relative to this file
            current_dir = Path(__file__).parent
            template_dir = current_dir.parent.parent / "templates"
        
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['timestamp'] = self._format_timestamp
        self.env.filters['severity_color'] = self._get_severity_color
    
    def generate_markdown_report(self, assessment_data: Dict, output_path: str) -> bool:
        """
        Generate markdown assessment report.
        
        Args:
            assessment_data: Complete assessment data
            output_path: Path to save the markdown report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.env.get_template('assessment-report.md.j2')
            
            # Prepare data for template
            template_data = {
                'assessment': assessment_data,
                'generation_time': datetime.utcnow().isoformat() + 'Z',
                'summary': self._generate_summary(assessment_data)
            }
            
            # Render template
            content = template.render(**template_data)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"Error generating markdown report: {e}")
            return False
    
    def generate_html_report(self, assessment_data: Dict, output_path: str) -> bool:
        """
        Generate HTML assessment report.
        
        Args:
            assessment_data: Complete assessment data
            output_path: Path to save the HTML report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.env.get_template('assessment-report.html.j2')
            
            # Prepare data for template
            template_data = {
                'assessment': assessment_data,
                'generation_time': datetime.utcnow().isoformat() + 'Z',
                'summary': self._generate_summary(assessment_data),
                'json_data': json.dumps(assessment_data, indent=2)
            }
            
            # Render template
            content = template.render(**template_data)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"Error generating HTML report: {e}")
            return False
    
    def generate_web_dashboard(self, assessment_data: Dict, output_dir: str) -> bool:
        """
        Generate interactive web dashboard.
        
        Args:
            assessment_data: Complete assessment data
            output_dir: Directory to save the web dashboard
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate main HTML file
            template = self.env.get_template('web-dashboard.html.j2')
            
            template_data = {
                'assessment': assessment_data,
                'generation_time': datetime.utcnow().isoformat() + 'Z',
                'summary': self._generate_summary(assessment_data)
            }
            
            content = template.render(**template_data)
            
            with open(output_path / 'index.html', 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Generate assessment data JSON
            with open(output_path / 'assessment-data.json', 'w', encoding='utf-8') as f:
                json.dump(assessment_data, f, indent=2)
            
            # Copy assets if they exist
            assets_src = self.template_dir / 'assets'
            if assets_src.exists():
                assets_dst = output_path / 'assets'
                self._copy_directory(assets_src, assets_dst)
            
            return True
            
        except Exception as e:
            print(f"Error generating web dashboard: {e}")
            return False
    
    def generate_json_report(self, assessment_data: Dict, output_path: str) -> bool:
        """
        Generate JSON assessment report.
        
        Args:
            assessment_data: Complete assessment data
            output_path: Path to save the JSON report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata
            report_data = {
                'metadata': {
                    'generation_time': datetime.utcnow().isoformat() + 'Z',
                    'version': '1.0.0',
                    'format': 'eks-upgrade-assessment'
                },
                'summary': self._generate_summary(assessment_data),
                'assessment_data': assessment_data
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error generating JSON report: {e}")
            return False
    
    def generate_deprecated_apis_report(self, deprecated_apis_data: Dict, output_path: str) -> bool:
        """
        Generate dedicated deprecated APIs report.
        
        Args:
            deprecated_apis_data: Deprecated APIs assessment data
            output_path: Path to save the report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.env.get_template('deprecated-apis-report.md.j2')
            
            template_data = {
                'deprecated_apis': deprecated_apis_data,
                'generation_time': datetime.utcnow().isoformat() + 'Z'
            }
            
            content = template.render(**template_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"Error generating deprecated APIs report: {e}")
            return False
    
    def generate_compatibility_matrix(self, compatibility_data: Dict, output_path: str) -> bool:
        """
        Generate compatibility matrix report.
        
        Args:
            compatibility_data: Compatibility assessment data
            output_path: Path to save the report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.env.get_template('compatibility-matrix.md.j2')
            
            template_data = {
                'compatibility': compatibility_data,
                'generation_time': datetime.utcnow().isoformat() + 'Z'
            }
            
            content = template.render(**template_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"Error generating compatibility matrix: {e}")
            return False
    
    def _generate_summary(self, assessment_data: Dict) -> Dict:
        """Generate assessment summary."""
        summary = {
            'total_clusters': 0,
            'clusters_ready': 0,
            'clusters_with_issues': 0,
            'total_issues': 0,
            'critical_issues': 0,
            'warnings': 0,
            'deprecated_apis_found': 0,
            'overall_readiness': 'unknown'
        }
        
        # Count clusters and issues
        clusters = assessment_data.get('clusters', [])
        summary['total_clusters'] = len(clusters)
        
        for cluster in clusters:
            cluster_name = cluster.get('cluster_name', 'unknown')
            has_issues = False
            
            # Check cluster insights
            insights = cluster.get('cluster_insights', {})
            if insights.get('upgrade_blockers'):
                summary['critical_issues'] += len(insights['upgrade_blockers'])
                has_issues = True
            
            if insights.get('warnings'):
                summary['warnings'] += len(insights['warnings'])
                has_issues = True
            
            # Check deprecated APIs
            deprecated_apis = cluster.get('deprecated_apis', {})
            kubent_results = deprecated_apis.get('kubent_results', {})
            pluto_results = deprecated_apis.get('pluto_results', {})
            
            if kubent_results.get('status') == 'success':
                kubent_summary = kubent_results.get('summary', {})
                summary['deprecated_apis_found'] += kubent_summary.get('total_deprecated', 0)
                if kubent_summary.get('total_deprecated', 0) > 0:
                    has_issues = True
            
            if pluto_results.get('status') == 'success':
                pluto_summary = pluto_results.get('summary', {})
                summary['deprecated_apis_found'] += pluto_summary.get('total_deprecated', 0)
                if pluto_summary.get('total_deprecated', 0) > 0:
                    has_issues = True
            
            # Check compatibility
            compatibility = cluster.get('compatibility', {})
            if not compatibility.get('compatible', True):
                summary['critical_issues'] += len(compatibility.get('issues', []))
                has_issues = True
            
            # Update cluster counts
            if has_issues:
                summary['clusters_with_issues'] += 1
            else:
                summary['clusters_ready'] += 1
        
        summary['total_issues'] = summary['critical_issues'] + summary['warnings']
        
        # Determine overall readiness
        if summary['total_clusters'] == 0:
            summary['overall_readiness'] = 'unknown'
        elif summary['critical_issues'] > 0:
            summary['overall_readiness'] = 'not_ready'
        elif summary['warnings'] > 0:
            summary['overall_readiness'] = 'ready_with_warnings'
        else:
            summary['overall_readiness'] = 'ready'
        
        return summary
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """Format timestamp for display."""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except Exception:
            return timestamp_str
    
    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity level."""
        colors = {
            'high': '#dc3545',
            'medium': '#fd7e14',
            'low': '#28a745',
            'critical': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        }
        return colors.get(severity.lower(), '#6c757d')
    
    def _copy_directory(self, src: Path, dst: Path):
        """Copy directory recursively."""
        import shutil
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
