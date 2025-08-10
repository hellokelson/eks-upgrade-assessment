"""
EKS Cluster Insights Integration

This module integrates with AWS EKS Cluster Insights to gather upgrade readiness information.
"""

import boto3
import json
from typing import Dict, List, Optional
from ..utils.aws_client import AWSClient


class ClusterInsightsAnalyzer:
    """Analyzes EKS clusters using AWS Cluster Insights."""
    
    def __init__(self, aws_client: AWSClient):
        self.aws_client = aws_client
        self.eks_client = aws_client.get_client('eks')
    
    def get_cluster_insights(self, cluster_name: str) -> Dict:
        """
        Retrieve cluster insights for a specific cluster.
        
        Args:
            cluster_name: Name of the EKS cluster
            
        Returns:
            Dictionary containing cluster insights data
        """
        try:
            # Get cluster insights
            response = self.eks_client.list_insights(
                clusterName=cluster_name
            )
            
            insights_data = {
                'cluster_name': cluster_name,
                'insights': [],
                'summary': {
                    'total_insights': 0,
                    'categories': {}
                }
            }
            
            for insight in response.get('insights', []):
                insight_detail = self.eks_client.describe_insight(
                    clusterName=cluster_name,
                    id=insight['id']
                )
                
                insights_data['insights'].append(insight_detail['insight'])
                
                # Update summary
                category = insight_detail['insight'].get('category', 'Unknown')
                insights_data['summary']['categories'][category] = \
                    insights_data['summary']['categories'].get(category, 0) + 1
            
            insights_data['summary']['total_insights'] = len(insights_data['insights'])
            
            return insights_data
            
        except Exception as e:
            print(f"Error retrieving cluster insights for {cluster_name}: {str(e)}")
            return {
                'cluster_name': cluster_name,
                'error': str(e),
                'insights': [],
                'summary': {'total_insights': 0, 'categories': {}}
            }
    
    def analyze_upgrade_readiness(self, cluster_name: str) -> Dict:
        """
        Analyze cluster upgrade readiness using insights.
        
        Args:
            cluster_name: Name of the EKS cluster
            
        Returns:
            Dictionary containing upgrade readiness analysis
        """
        insights = self.get_cluster_insights(cluster_name)
        
        upgrade_analysis = {
            'cluster_name': cluster_name,
            'upgrade_blockers': [],
            'warnings': [],
            'recommendations': [],
            'readiness_score': 100
        }
        
        for insight in insights.get('insights', []):
            severity = insight.get('severity', 'LOW')
            category = insight.get('category', 'Unknown')
            
            if severity == 'HIGH':
                upgrade_analysis['upgrade_blockers'].append({
                    'id': insight.get('id'),
                    'name': insight.get('name'),
                    'description': insight.get('description'),
                    'category': category,
                    'recommendation': insight.get('recommendation')
                })
                upgrade_analysis['readiness_score'] -= 30
                
            elif severity == 'MEDIUM':
                upgrade_analysis['warnings'].append({
                    'id': insight.get('id'),
                    'name': insight.get('name'),
                    'description': insight.get('description'),
                    'category': category,
                    'recommendation': insight.get('recommendation')
                })
                upgrade_analysis['readiness_score'] -= 15
                
            else:  # LOW severity
                upgrade_analysis['recommendations'].append({
                    'id': insight.get('id'),
                    'name': insight.get('name'),
                    'description': insight.get('description'),
                    'category': category,
                    'recommendation': insight.get('recommendation')
                })
                upgrade_analysis['readiness_score'] -= 5
        
        # Ensure score doesn't go below 0
        upgrade_analysis['readiness_score'] = max(0, upgrade_analysis['readiness_score'])
        
        return upgrade_analysis
