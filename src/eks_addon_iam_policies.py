"""
EKS Addon IAM Policy Mapping

This module defines which EKS addons require IAM roles and their corresponding
AWS managed policies. This data is used to validate addon IAM configurations.
"""

from typing import Dict, List, Any
import json
from pathlib import Path


# Comprehensive mapping of EKS addons to their required AWS managed policies
EKS_ADDON_IAM_POLICIES = {
    # Storage CSI Drivers
    "aws-ebs-csi-driver": {
        "description": "Amazon EBS CSI Driver for persistent volume support",
        "requires_iam": True,
        "managed_policies": [
            "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
        ],
        "service_account": "ebs-csi-controller-sa",
        "namespace": "kube-system"
    },
    "aws-efs-csi-driver": {
        "description": "Amazon EFS CSI Driver for shared file system support",
        "requires_iam": True,
        "managed_policies": [
            "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"
        ],
        "service_account": "efs-csi-controller-sa",
        "namespace": "kube-system"
    },
    "aws-fsx-csi-driver": {
        "description": "Amazon FSx CSI Driver for high-performance file systems",
        "requires_iam": True,
        "managed_policies": [
            "arn:aws:iam::aws:policy/service-role/AmazonFSxCSIDriverServiceRolePolicy"
        ],
        "service_account": "fsx-csi-controller-sa",
        "namespace": "kube-system"
    },
    "aws-mountpoint-s3-csi-driver": {
        "description": "Mountpoint for Amazon S3 CSI Driver",
        "requires_iam": True,
        "managed_policies": [
            # Note: This typically requires custom policies for specific S3 buckets
            "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"  # Minimum, usually needs custom
        ],
        "service_account": "s3-csi-driver-sa",
        "namespace": "kube-system",
        "note": "Usually requires custom policies for specific S3 bucket access"
    },
    
    # Load Balancing
    "aws-load-balancer-controller": {
        "description": "AWS Load Balancer Controller for ALB/NLB integration",
        "requires_iam": True,
        "managed_policies": [
            # Note: AWS Load Balancer Controller typically uses a custom policy
            # The managed policy below is a simplified version
        ],
        "service_account": "aws-load-balancer-controller",
        "namespace": "kube-system",
        "note": "Typically requires custom IAM policy with specific permissions",
        "custom_policy_required": True
    },
    
    # Observability and Monitoring
    "amazon-cloudwatch-observability": {
        "description": "Amazon CloudWatch Observability add-on",
        "requires_iam": True,
        "managed_policies": [
            "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
            "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
        ],
        "service_account": "cloudwatch-agent",
        "namespace": "amazon-cloudwatch"
    },
    "adot": {
        "description": "AWS Distro for OpenTelemetry (ADOT)",
        "requires_iam": True,
        "managed_policies": [
            "arn:aws:iam::aws:policy/AmazonPrometheusRemoteWriteAccess",
            "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
            "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
        ],
        "service_account": "adot-collector",
        "namespace": "opentelemetry-operator-system"
    },
    
    # Security
    "aws-guardduty-agent": {
        "description": "Amazon GuardDuty security monitoring agent",
        "requires_iam": True,
        "managed_policies": [
            "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
        ],
        "service_account": "aws-guardduty-agent",
        "namespace": "amazon-guardduty"
    },
    
    # Core EKS Addons - Some may require IAM depending on configuration
    "vpc-cni": {
        "description": "Amazon VPC CNI plugin for pod networking",
        "requires_iam": True,  # VPC CNI often needs IAM policies for advanced features
        "managed_policies": [
            "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
        ],
        "service_account": "aws-node",
        "namespace": "kube-system",
        "note": "Required for advanced VPC CNI features like pod-level security groups, IPv6, custom networking"
    },
    "coredns": {
        "description": "CoreDNS for cluster DNS resolution",
        "requires_iam": False,
        "managed_policies": [],
        "note": "No additional IAM permissions required"
    },
    "kube-proxy": {
        "description": "Kubernetes network proxy",
        "requires_iam": False,
        "managed_policies": [],
        "note": "No additional IAM permissions required"
    },
    "eks-pod-identity-agent": {
        "description": "EKS Pod Identity Agent for IAM roles for service accounts",
        "requires_iam": False,
        "managed_policies": [],
        "note": "Manages IAM for other pods, no additional permissions needed"
    },
    "snapshot-controller": {
        "description": "Volume snapshot controller for CSI drivers",
        "requires_iam": False,
        "managed_policies": [],
        "note": "No additional IAM permissions required"
    },
    
    # Third-party addons commonly used
    "metrics-server": {
        "description": "Kubernetes Metrics Server for resource metrics",
        "requires_iam": False,
        "managed_policies": [],
        "note": "No additional IAM permissions required"
    }
}


def generate_addon_iam_mapping() -> Dict[str, Any]:
    """Generate the complete addon IAM policy mapping."""
    return {
        "metadata": {
            "generated_at": "2025-08-13T08:42:55.987Z",
            "description": "EKS Addon IAM Policy Requirements Mapping",
            "version": "1.0.0"
        },
        "addon_iam_policies": EKS_ADDON_IAM_POLICIES,
        "summary": {
            "total_addons": len(EKS_ADDON_IAM_POLICIES),
            "require_iam": len([k for k, v in EKS_ADDON_IAM_POLICIES.items() if v["requires_iam"]]),
            "no_iam_required": len([k for k, v in EKS_ADDON_IAM_POLICIES.items() if not v["requires_iam"]])
        }
    }


def save_addon_iam_mapping(output_dir: Path) -> Path:
    """Save the addon IAM mapping to shared data directory."""
    shared_data_dir = output_dir / "shared-data"
    shared_data_dir.mkdir(parents=True, exist_ok=True)
    
    mapping_file = shared_data_dir / "eks-addon-iam-policies.json"
    mapping_data = generate_addon_iam_mapping()
    
    with open(mapping_file, 'w') as f:
        json.dump(mapping_data, f, indent=2)
    
    return mapping_file


def load_addon_iam_mapping(shared_data_dir: Path) -> Dict[str, Any]:
    """Load the addon IAM mapping from shared data directory."""
    mapping_file = shared_data_dir / "eks-addon-iam-policies.json"
    
    if not mapping_file.exists():
        # Return default mapping if file doesn't exist
        return generate_addon_iam_mapping()
    
    with open(mapping_file, 'r') as f:
        return json.load(f)


def get_addon_iam_requirements(addon_name: str, shared_data_dir: Path = None) -> Dict[str, Any]:
    """Get IAM requirements for a specific addon."""
    if shared_data_dir:
        mapping_data = load_addon_iam_mapping(shared_data_dir)
    else:
        mapping_data = generate_addon_iam_mapping()
    
    return mapping_data["addon_iam_policies"].get(addon_name, {
        "description": f"Unknown addon: {addon_name}",
        "requires_iam": None,
        "managed_policies": [],
        "note": "Addon not found in IAM policy mapping - manual verification required"
    })
