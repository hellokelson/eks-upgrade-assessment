"""
EKS Addon IAM Role and Policy Analyzer

This module analyzes EKS addon IAM roles and policies to ensure they meet
AWS requirements for addon functionality and upgrades.
"""

import boto3
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import click


@dataclass
class IAMPolicyInfo:
    """Information about an IAM policy."""
    policy_arn: str
    policy_name: str
    is_aws_managed: bool
    version: Optional[str] = None


@dataclass
class IAMRoleInfo:
    """Information about an IAM role."""
    role_name: str
    role_arn: str
    attached_policies: List[IAMPolicyInfo]
    trust_policy: Dict[str, Any]


@dataclass
class AddonIAMAnalysis:
    """Analysis result for an addon's IAM configuration."""
    addon_name: str
    service_account_role_arn: Optional[str]
    iam_role_info: Optional[IAMRoleInfo]
    expected_managed_policies: List[str]
    validation_status: str  # 'pass', 'warning', 'error', 'not_applicable'
    issues: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'addon_name': self.addon_name,
            'service_account_role_arn': self.service_account_role_arn,
            'iam_role_info': {
                'role_name': self.iam_role_info.role_name,
                'role_arn': self.iam_role_info.role_arn,
                'attached_policies': [
                    {
                        'policy_arn': p.policy_arn,
                        'policy_name': p.policy_name,
                        'is_aws_managed': p.is_aws_managed,
                        'version': p.version
                    } for p in self.iam_role_info.attached_policies
                ],
                'trust_policy': self.iam_role_info.trust_policy
            } if self.iam_role_info else None,
            'expected_managed_policies': self.expected_managed_policies,
            'validation_status': self.validation_status,
            'issues': self.issues,
            'recommendations': self.recommendations
        }


class AddonIAMAnalyzer:
    """Analyzes EKS addon IAM roles and policies."""
    
    def __init__(self, aws_client, shared_data_dir=None):
        """Initialize the analyzer with AWS clients."""
        self.aws_client = aws_client
        self.eks_client = aws_client.eks_client
        self.iam_client = aws_client.iam_client
        self.shared_data_dir = shared_data_dir
        
        # Load IAM policy mapping from shared data
        if shared_data_dir:
            from eks_addon_iam_policies import load_addon_iam_mapping
            self.iam_mapping_data = load_addon_iam_mapping(Path(shared_data_dir))
        else:
            from eks_addon_iam_policies import generate_addon_iam_mapping
            self.iam_mapping_data = generate_addon_iam_mapping()
        
        self.addon_iam_policies = self.iam_mapping_data.get('addon_iam_policies', {})
    
    def analyze_cluster_addon_iam(self, cluster_name: str, addons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze IAM configuration for all addons in a cluster."""
        click.echo(f"    🔐 Analyzing addon IAM roles and policies...")
        
        analysis_results = {
            'cluster_name': cluster_name,
            'addon_iam_analysis': [],
            'summary': {
                'total_addons': len(addons),
                'pass': 0,
                'warning': 0,
                'error': 0,
                'not_applicable': 0
            },
            'recommendations': []
        }
        
        for addon in addons:
            addon_name = addon.get('name', addon.get('addonName', ''))
            addon_analysis = self._analyze_single_addon_iam(cluster_name, addon_name, addon)
            analysis_results['addon_iam_analysis'].append(addon_analysis.to_dict())
            
            # Update summary
            status = addon_analysis.validation_status
            analysis_results['summary'][status] = analysis_results['summary'].get(status, 0) + 1
        
        # Generate cluster-level recommendations
        analysis_results['recommendations'] = self._generate_cluster_recommendations(
            [addon_analysis for addon_analysis in analysis_results['addon_iam_analysis']]
        )
        
        return analysis_results
    
    def _analyze_single_addon_iam(self, cluster_name: str, addon_name: str, addon_info: Dict[str, Any]) -> AddonIAMAnalysis:
        """Analyze IAM configuration for a single addon."""
        try:
            # Get addon IAM requirements from mapping
            addon_requirements = self.addon_iam_policies.get(addon_name, {})
            requires_iam = addon_requirements.get('requires_iam', None)
            expected_policies = addon_requirements.get('managed_policies', [])
            
            # Get detailed addon information
            response = self.eks_client.describe_addon(
                clusterName=cluster_name,
                addonName=addon_name
            )
            addon_details = response.get('addon', {})
            
            # Extract service account role ARN
            service_account_role_arn = addon_details.get('serviceAccountRoleArn')
            
            # If addon doesn't require IAM
            if requires_iam is False:
                return AddonIAMAnalysis(
                    addon_name=addon_name,
                    service_account_role_arn=service_account_role_arn,
                    iam_role_info=None,
                    expected_managed_policies=expected_policies,
                    validation_status='not_applicable',
                    issues=[],
                    recommendations=[]
                )
            
            # If addon requirements are unknown
            if requires_iam is None:
                return AddonIAMAnalysis(
                    addon_name=addon_name,
                    service_account_role_arn=service_account_role_arn,
                    iam_role_info=None,
                    expected_managed_policies=[],
                    validation_status='warning',
                    issues=[f'Unknown addon: {addon_name} - IAM requirements not defined'],
                    recommendations=['Manual verification required - check addon documentation for IAM requirements']
                )
            
            # If no service account role, check if one is expected
            if not service_account_role_arn:
                if requires_iam:
                    return AddonIAMAnalysis(
                        addon_name=addon_name,
                        service_account_role_arn=None,
                        iam_role_info=None,
                        expected_managed_policies=expected_policies,
                        validation_status='error',
                        issues=[f'Addon {addon_name} requires IAM role but none is configured'],
                        recommendations=[f'Configure IAM role with required policies: {", ".join([p.split("/")[-1] for p in expected_policies])}']
                    )
                else:
                    return AddonIAMAnalysis(
                        addon_name=addon_name,
                        service_account_role_arn=None,
                        iam_role_info=None,
                        expected_managed_policies=[],
                        validation_status='not_applicable',
                        issues=[],
                        recommendations=[]
                    )
            
            # Analyze the IAM role
            iam_role_info = self._get_iam_role_info(service_account_role_arn)
            
            # Validate IAM configuration
            validation_result = self._validate_iam_configuration(
                addon_name, iam_role_info, expected_policies, addon_requirements
            )
            
            return AddonIAMAnalysis(
                addon_name=addon_name,
                service_account_role_arn=service_account_role_arn,
                iam_role_info=iam_role_info,
                expected_managed_policies=expected_policies,
                validation_status=validation_result['status'],
                issues=validation_result['issues'],
                recommendations=validation_result['recommendations']
            )
            
        except Exception as e:
            click.echo(f"      ⚠️  Warning: Could not analyze IAM for addon {addon_name}: {str(e)}")
            return AddonIAMAnalysis(
                addon_name=addon_name,
                service_account_role_arn=None,
                iam_role_info=None,
                expected_managed_policies=[],
                validation_status='error',
                issues=[f'Failed to analyze IAM configuration: {str(e)}'],
                recommendations=['Manual verification required']
            )
    
    def _get_iam_role_info(self, role_arn: str) -> Optional[IAMRoleInfo]:
        """Get detailed information about an IAM role."""
        try:
            # Extract role name from ARN
            role_name = role_arn.split('/')[-1]
            
            # Get role details
            role_response = self.iam_client.get_role(RoleName=role_name)
            role_data = role_response['Role']
            
            # Get attached policies
            policies_response = self.iam_client.list_attached_role_policies(RoleName=role_name)
            attached_policies = []
            
            for policy in policies_response['AttachedPolicies']:
                policy_info = IAMPolicyInfo(
                    policy_arn=policy['PolicyArn'],
                    policy_name=policy['PolicyName'],
                    is_aws_managed=policy['PolicyArn'].startswith('arn:aws:iam::aws:policy/')
                )
                attached_policies.append(policy_info)
            
            click.echo(f"      📋 Found IAM role: {role_name} with {len(attached_policies)} policies")
            for policy in attached_policies:
                policy_type = "AWS Managed" if policy.is_aws_managed else "Custom"
                click.echo(f"        - {policy.policy_name} ({policy_type})")
            
            return IAMRoleInfo(
                role_name=role_name,
                role_arn=role_arn,
                attached_policies=attached_policies,
                trust_policy=role_data.get('AssumeRolePolicyDocument', {})
            )
            
        except Exception as e:
            click.echo(f"      ⚠️  Warning: Could not get IAM role info for {role_arn}: {str(e)}")
            return None
    
    def _validate_iam_configuration(self, addon_name: str, iam_role_info: Optional[IAMRoleInfo], 
                                   expected_policies: List[str], addon_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Validate IAM role configuration against expected policies."""
        if not iam_role_info:
            return {
                'status': 'error',
                'issues': ['Could not retrieve IAM role information'],
                'recommendations': ['Verify IAM role exists and is accessible']
            }
        
        if not expected_policies:
            # Check if this addon typically requires custom policies
            if addon_requirements.get('custom_policy_required', False):
                custom_policies = [p for p in iam_role_info.attached_policies if not p.is_aws_managed]
                if custom_policies:
                    return {
                        'status': 'warning',
                        'issues': [f'Using custom policies: {", ".join([p.policy_name for p in custom_policies])}'],
                        'recommendations': ['Verify custom policies provide required permissions for addon functionality']
                    }
                else:
                    return {
                        'status': 'warning',
                        'issues': ['Addon typically requires custom IAM policies but none found'],
                        'recommendations': ['Review addon documentation and configure appropriate IAM policies']
                    }
            else:
                return {
                    'status': 'not_applicable',
                    'issues': [],
                    'recommendations': []
                }
        
        issues = []
        recommendations = []
        attached_policy_arns = [p.policy_arn for p in iam_role_info.attached_policies]
        
        # Check if all expected managed policies are attached
        missing_policies = []
        for expected_policy in expected_policies:
            if expected_policy not in attached_policy_arns:
                missing_policies.append(expected_policy)
        
        # Check if using custom policies instead of managed policies
        custom_policies = [p for p in iam_role_info.attached_policies if not p.is_aws_managed]
        
        if missing_policies and custom_policies:
            # Has custom policies but missing some managed policies
            return {
                'status': 'warning',
                'issues': [
                    f'Missing expected AWS managed policies: {", ".join([p.split("/")[-1] for p in missing_policies])}',
                    f'Using custom policies: {", ".join([p.policy_name for p in custom_policies])}'
                ],
                'recommendations': [
                    'Verify custom policies provide equivalent permissions to AWS managed policies',
                    f'Consider using AWS managed policies: {", ".join([p.split("/")[-1] for p in missing_policies])}'
                ]
            }
        elif missing_policies:
            # Missing managed policies, no custom policies
            return {
                'status': 'error',
                'issues': [f'Missing required AWS managed policies: {", ".join([p.split("/")[-1] for p in missing_policies])}'],
                'recommendations': [f'Attach required policies: {", ".join([p.split("/")[-1] for p in missing_policies])}']
            }
        elif custom_policies:
            # Has all managed policies but also has custom policies
            return {
                'status': 'warning',
                'issues': [f'Using additional custom policies: {", ".join([p.policy_name for p in custom_policies])}'],
                'recommendations': ['Verify custom policies are necessary and follow least privilege principle']
            }
        else:
            # All good - using only expected managed policies
            return {
                'status': 'pass',
                'issues': [],
                'recommendations': []
            }
    
    def _generate_cluster_recommendations(self, addon_analyses: List[Dict[str, Any]]) -> List[str]:
        """Generate cluster-level IAM recommendations."""
        recommendations = []
        
        error_addons = [a for a in addon_analyses if a.get('validation_status') == 'error']
        warning_addons = [a for a in addon_analyses if a.get('validation_status') == 'warning']
        
        if error_addons:
            recommendations.append(
                f'Critical: {len(error_addons)} addon(s) have IAM configuration errors that must be fixed before upgrade'
            )
        
        if warning_addons:
            recommendations.append(
                f'Review: {len(warning_addons)} addon(s) use custom IAM policies that should be verified for compatibility'
            )
        
        if not error_addons and not warning_addons:
            recommendations.append('All addon IAM configurations are using AWS managed policies as recommended')
        
        return recommendations


def analyze_cluster_addon_iam_roles(cluster_name: str, addons: List[Dict[str, Any]], aws_client, shared_data_dir=None) -> Dict[str, Any]:
    """Analyze IAM roles and policies for cluster addons."""
    analyzer = AddonIAMAnalyzer(aws_client, shared_data_dir)
    return analyzer.analyze_cluster_addon_iam(cluster_name, addons)
