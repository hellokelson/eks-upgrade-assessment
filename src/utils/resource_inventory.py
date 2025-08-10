"""AWS resource inventory generator for EKS clusters."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .aws_client import AWSClient


@dataclass
class AWSResourceInventory:
    """AWS resource inventory for an EKS cluster."""
    cluster_name: str
    iam_resources: Dict[str, Any]
    networking_resources: Dict[str, Any]
    storage_resources: Dict[str, Any]
    monitoring_resources: Dict[str, Any]
    addons_resources: Dict[str, Any]
    secrets_resources: Dict[str, Any]


class ResourceInventoryGenerator:
    """Generate comprehensive AWS resource inventory for EKS clusters."""
    
    def __init__(self, aws_client: AWSClient):
        self.aws_client = aws_client
    
    def generate_inventory(self, cluster_name: str) -> AWSResourceInventory:
        """Generate complete resource inventory for a cluster."""
        return AWSResourceInventory(
            cluster_name=cluster_name,
            iam_resources=self._get_iam_resources(cluster_name),
            networking_resources=self._get_networking_resources(cluster_name),
            storage_resources=self._get_storage_resources(cluster_name),
            monitoring_resources=self._get_monitoring_resources(cluster_name),
            addons_resources=self._get_addons_resources(cluster_name),
            secrets_resources=self._get_secrets_resources(cluster_name)
        )
    
    def _get_iam_resources(self, cluster_name: str) -> Dict[str, Any]:
        """Get IAM resources associated with the cluster."""
        resources = {
            'cluster_service_role': None,
            'node_instance_roles': [],
            'fargate_execution_roles': [],
            'irsa_roles': [],
            'oidc_provider': None,
            'custom_policies': []
        }
        
        try:
            # Get cluster info to find service role
            cluster_info = self.aws_client.get_cluster_info(cluster_name)
            if cluster_info:
                resources['cluster_service_role'] = cluster_info.role_arn
                
                # Get OIDC provider info
                if cluster_info.identity and 'oidc' in cluster_info.identity:
                    resources['oidc_provider'] = cluster_info.identity['oidc']
            
            # Get node group roles
            node_groups = self.aws_client.get_node_groups(cluster_name)
            for ng in node_groups:
                if ng.node_role and ng.node_role not in resources['node_instance_roles']:
                    resources['node_instance_roles'].append(ng.node_role)
            
            # Get Fargate profile roles
            fargate_profiles = self.aws_client.get_fargate_profiles(cluster_name)
            for profile in fargate_profiles:
                if 'podExecutionRoleArn' in profile:
                    role_arn = profile['podExecutionRoleArn']
                    if role_arn not in resources['fargate_execution_roles']:
                        resources['fargate_execution_roles'].append(role_arn)
            
        except Exception as e:
            print(f"Warning: Failed to get IAM resources for {cluster_name}: {str(e)}")
        
        return resources
    
    def _get_networking_resources(self, cluster_name: str) -> Dict[str, Any]:
        """Get networking resources associated with the cluster."""
        resources = {
            'vpc_id': None,
            'subnet_ids': [],
            'security_group_ids': [],
            'load_balancers': [],
            'target_groups': []
        }
        
        try:
            cluster_info = self.aws_client.get_cluster_info(cluster_name)
            if cluster_info and cluster_info.vpc_config:
                vpc_config = cluster_info.vpc_config
                resources['vpc_id'] = vpc_config.get('vpcId')
                resources['subnet_ids'] = vpc_config.get('subnetIds', [])
                resources['security_group_ids'] = vpc_config.get('securityGroupIds', [])
                
                # Add cluster security group
                cluster_sg = vpc_config.get('clusterSecurityGroupId')
                if cluster_sg and cluster_sg not in resources['security_group_ids']:
                    resources['security_group_ids'].append(cluster_sg)
            
            # Note: Load balancers and target groups would require additional API calls
            # to ELBv2 service to discover resources created by AWS Load Balancer Controller
            
        except Exception as e:
            print(f"Warning: Failed to get networking resources for {cluster_name}: {str(e)}")
        
        return resources
    
    def _get_storage_resources(self, cluster_name: str) -> Dict[str, Any]:
        """Get storage resources associated with the cluster."""
        resources = {
            'ebs_volumes': [],
            'efs_filesystems': [],
            'fsx_filesystems': [],
            'storage_classes': []
        }
        
        # Note: This would require Kubernetes API access to discover
        # PersistentVolumes and their associated AWS resources
        # For now, we'll provide placeholders and instructions
        
        return resources
    
    def _get_monitoring_resources(self, cluster_name: str) -> Dict[str, Any]:
        """Get monitoring and logging resources."""
        resources = {
            'cloudwatch_log_groups': [],
            'cloudwatch_alarms': [],
            'xray_configuration': None
        }
        
        try:
            # Check for common EKS log groups
            common_log_groups = [
                f'/aws/eks/{cluster_name}/cluster',
                f'/aws/containerinsights/{cluster_name}/application',
                f'/aws/containerinsights/{cluster_name}/dataplane',
                f'/aws/containerinsights/{cluster_name}/host',
                f'/aws/containerinsights/{cluster_name}/performance'
            ]
            
            for log_group in common_log_groups:
                try:
                    response = self.aws_client.logs_client.describe_log_groups(
                        logGroupNamePrefix=log_group,
                        limit=1
                    )
                    if response.get('logGroups'):
                        resources['cloudwatch_log_groups'].append(log_group)
                except:
                    # Log group doesn't exist, skip
                    pass
                    
        except Exception as e:
            print(f"Warning: Failed to get monitoring resources for {cluster_name}: {str(e)}")
        
        return resources
    
    def _get_addons_resources(self, cluster_name: str) -> Dict[str, Any]:
        """Get EKS addons and extensions."""
        resources = {
            'eks_addons': [],
            'aws_load_balancer_controller': None,
            'cluster_autoscaler': None,
            'external_dns': None
        }
        
        try:
            # Get EKS managed addons
            addons = self.aws_client.get_addons(cluster_name)
            resources['eks_addons'] = addons
            
            # Note: Other controllers would require Kubernetes API access to detect
            
        except Exception as e:
            print(f"Warning: Failed to get addons resources for {cluster_name}: {str(e)}")
        
        return resources
    
    def _get_secrets_resources(self, cluster_name: str) -> Dict[str, Any]:
        """Get secrets and configuration resources."""
        resources = {
            'secrets_manager_secrets': [],
            'parameter_store_parameters': [],
            'ecr_repositories': []
        }
        
        # Note: This would require additional logic to discover
        # secrets and parameters used by the cluster workloads
        
        return resources
    
    def generate_inventory_markdown(self, inventory: AWSResourceInventory) -> str:
        """Generate markdown documentation for the resource inventory."""
        md_content = f"""# AWS Resources Inventory - {inventory.cluster_name}

⚠️ **CRITICAL**: These AWS resources are NOT backed up by Velero and must be manually recreated if needed.

## EKS Cluster Infrastructure

### Cluster Service Role
- **Role ARN**: `{inventory.iam_resources.get('cluster_service_role', 'Not found')}`
- **Purpose**: Allows EKS to manage AWS resources on your behalf
- **Recreation**: Must be recreated with proper EKS service permissions

### Node Groups and Instance Roles
"""
        
        node_roles = inventory.iam_resources.get('node_instance_roles', [])
        if node_roles:
            for role in node_roles:
                md_content += f"- **Role ARN**: `{role}`\n"
        else:
            md_content += "- No managed node groups found\n"
        
        md_content += """
### Fargate Execution Roles
"""
        
        fargate_roles = inventory.iam_resources.get('fargate_execution_roles', [])
        if fargate_roles:
            for role in fargate_roles:
                md_content += f"- **Role ARN**: `{role}`\n"
        else:
            md_content += "- No Fargate profiles found\n"
        
        md_content += f"""
### OIDC Identity Provider
- **OIDC Provider**: `{inventory.iam_resources.get('oidc_provider', {}).get('issuer', 'Not configured')}`
- **Purpose**: Enables IRSA (IAM Roles for Service Accounts)
- **Recreation**: Must be recreated for IRSA functionality

## Networking Resources

### VPC Configuration
- **VPC ID**: `{inventory.networking_resources.get('vpc_id', 'Not found')}`
- **Subnets**: {len(inventory.networking_resources.get('subnet_ids', []))} subnets
- **Security Groups**: {len(inventory.networking_resources.get('security_group_ids', []))} security groups

### Security Groups
"""
        
        security_groups = inventory.networking_resources.get('security_group_ids', [])
        for sg in security_groups:
            md_content += f"- `{sg}`\n"
        
        md_content += """
### Load Balancers and Target Groups
⚠️ **Manual Discovery Required**: Use AWS Console or CLI to identify:
- Application Load Balancers (ALB) created by AWS Load Balancer Controller
- Network Load Balancers (NLB) created by Kubernetes services
- Target Groups associated with load balancers

```bash
# Discover load balancers
aws elbv2 describe-load-balancers --query 'LoadBalancers[?contains(Tags[?Key==`kubernetes.io/cluster/{cluster_name}`], `owned`) || contains(Tags[?Key==`kubernetes.io/cluster/{cluster_name}`], `shared`)]'

# Discover target groups
aws elbv2 describe-target-groups --query 'TargetGroups[?contains(Tags[?Key==`kubernetes.io/cluster/{cluster_name}`], `owned`) || contains(Tags[?Key==`kubernetes.io/cluster/{cluster_name}`], `shared`)]'
```

## Storage Resources

### Persistent Volumes
⚠️ **Kubernetes API Required**: Use kubectl to discover storage resources:

```bash
# List persistent volumes
kubectl get pv

# List storage classes
kubectl get storageclass

# Find EBS volumes
kubectl get pv -o jsonpath='{{range .items[*]}}{{.spec.awsElasticBlockStore.volumeID}}{{"\n"}}{{end}}'
```

### EFS and FSx File Systems
⚠️ **Manual Discovery Required**: Check for EFS and FSx resources used by the cluster:

```bash
# List EFS file systems
aws efs describe-file-systems

# List FSx file systems  
aws fsx describe-file-systems
```

## Monitoring and Logging

### CloudWatch Log Groups
"""
        
        log_groups = inventory.monitoring_resources.get('cloudwatch_log_groups', [])
        if log_groups:
            for log_group in log_groups:
                md_content += f"- `{log_group}`\n"
        else:
            md_content += "- No CloudWatch log groups found\n"
        
        md_content += """
### CloudWatch Alarms
⚠️ **Manual Discovery Required**: Check for EKS-related CloudWatch alarms:

```bash
# List CloudWatch alarms
aws cloudwatch describe-alarms --query 'MetricAlarms[?contains(MetricName, `eks`) || contains(AlarmName, `{cluster_name}`)]'
```

## EKS Add-ons and Extensions

### EKS Managed Add-ons
"""
        
        eks_addons = inventory.addons_resources.get('eks_addons', [])
        if eks_addons:
            for addon in eks_addons:
                addon_name = addon.get('addonName', 'Unknown')
                addon_version = addon.get('addonVersion', 'Unknown')
                md_content += f"- **{addon_name}**: Version `{addon_version}`\n"
        else:
            md_content += "- No EKS managed add-ons found\n"
        
        md_content += """
### Third-party Controllers
⚠️ **Manual Discovery Required**: Check for these common controllers:

- **AWS Load Balancer Controller**: Manages ALB/NLB resources
- **Cluster Autoscaler**: Manages node scaling
- **External DNS**: Manages Route53 DNS records
- **EBS CSI Driver**: Manages EBS volume provisioning
- **EFS CSI Driver**: Manages EFS volume provisioning

```bash
# Check for AWS Load Balancer Controller
kubectl get deployment -n kube-system aws-load-balancer-controller

# Check for Cluster Autoscaler
kubectl get deployment -n kube-system cluster-autoscaler

# Check for External DNS
kubectl get deployment -n kube-system external-dns
```

## Secrets and Configuration

### AWS Secrets Manager
⚠️ **Application-Specific**: Review your applications for Secrets Manager usage:

```bash
# List secrets (filter by your application tags)
aws secretsmanager list-secrets
```

### Systems Manager Parameter Store
⚠️ **Application-Specific**: Review your applications for Parameter Store usage:

```bash
# List parameters (filter by your application paths)
aws ssm describe-parameters
```

### ECR Repositories
⚠️ **Container Images**: Ensure your container images are available:

```bash
# List ECR repositories
aws ecr describe-repositories
```

## Recreation Checklist

### Before Cluster Restoration
- [ ] Document all IAM roles and policies
- [ ] Export VPC and networking configurations
- [ ] Backup EBS snapshots for persistent volumes
- [ ] Document load balancer configurations
- [ ] Export CloudWatch alarms and dashboards
- [ ] List all EKS add-ons and versions
- [ ] Document third-party controller configurations
- [ ] Export secrets and configuration parameters

### After Cluster Restoration
- [ ] Recreate IAM roles and policies
- [ ] Configure OIDC identity provider
- [ ] Restore networking configurations
- [ ] Recreate load balancers and target groups
- [ ] Restore persistent volumes from snapshots
- [ ] Reinstall and configure EKS add-ons
- [ ] Redeploy third-party controllers
- [ ] Restore secrets and configuration parameters
- [ ] Recreate CloudWatch alarms and dashboards
- [ ] Test all integrations and functionality

## Automation Recommendations

Consider using Infrastructure as Code (IaC) tools to manage these resources:

- **Terraform**: Define all AWS resources as code
- **CloudFormation**: Use AWS native IaC solution
- **CDK**: Use AWS Cloud Development Kit for programmatic resource management
- **Pulumi**: Modern IaC with multiple language support

This ensures reproducible and version-controlled infrastructure management.
"""
        
        return md_content