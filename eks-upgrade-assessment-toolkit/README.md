# EKS Upgrade Assessment Toolkit

A comprehensive toolkit to assess EKS cluster readiness for upgrades following AWS best practices. This toolkit focuses on thorough assessment and analysis to help you make informed upgrade decisions.

## Project Status

✅ **INITIALIZED** - The project structure has been set up with all core components:

- ✅ Complete module structure (`src/assessment/`, `src/generators/`, `src/utils/`)
- ✅ Assessment modules (cluster insights, deprecated APIs, compatibility, workload analysis)
- ✅ Report generators (Markdown, HTML, JSON, web dashboard)
- ✅ Script generators (validation, collection, scanning scripts)
- ✅ Jinja2 templates for reports and scripts
- ✅ Test framework setup
- ✅ Development tools (Makefile, setup.py)
- ✅ Documentation and configuration examples

## Features

- **Automated Cluster Discovery**: Automatically discovers all EKS clusters in your region
- **Comprehensive Assessment**: Integrates with EKS Cluster Insights, kubent, and pluto for deprecated API detection
- **Cluster Metadata Collection**: Collects and organizes all cluster configuration data
- **Risk Analysis**: Identifies potential upgrade risks and compatibility issues
- **Interactive Reports**: Generates HTML and markdown assessment reports
- **Standalone Metadata Generator**: Independent module for cluster metadata collection

## Installation

### Quick Setup

1. Install dependencies:
   ```bash
   make install
   # or manually:
   pip install -r requirements.txt
   pip install -e .
   ```

2. Install external tools (optional but recommended):
   ```bash
   make install-tools
   # or manually:
   ./install-tools.sh
   ```

3. Set up development environment (if contributing):
   ```bash
   make setup-dev
   ```

### Manual Installation

1. Clone or download the toolkit
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install required assessment tools (kubent and pluto):
   ```bash
   python src/main.py install-tools
   ```
   Or manually run the installation script:
   ```bash
   ./install-tools.sh
   ```
4. Restart your terminal or reload your shell:
   ```bash
   source ~/.bashrc
   ```
5. Verify tool installation:
   ```bash
   kubent --version
   pluto version
   ```

## Quick Start

### Using Make Commands

1. **Run Example Assessment**:
   ```bash
   make run-example
   ```

2. **Run Tests**:
   ```bash
   make test
   ```

3. **View All Available Commands**:
   ```bash
   make help
   ```

### Manual Usage

1. **Initialize Configuration**:
   ```bash
   python src/main.py init
   ```

2. **Install Assessment Tools**:
   ```bash
   python src/main.py install-tools
   # Restart terminal or run: source ~/.bashrc
   ```

3. **Edit Configuration**: Modify `eks-upgrade-config.yaml` to match your environment

4. **Validate Configuration**:
   ```bash
   python src/main.py validate
   ```

5. **Run Assessment** (kubectl is auto-configured for each cluster):
   ```bash
   python src/main.py analyze
   ```

## Configuration Options

The toolkit uses a YAML configuration file with the following structure:

```yaml
aws_configuration:
  region: "us-west-2"                    # AWS region
  credentials_profile: "default"         # AWS credentials profile

cluster_info:
  cluster_names: []                      # Empty = auto-discover all clusters
  current_control_plane_version: null   # Auto-detected if not specified
  current_data_plane_version: null      # Auto-detected if not specified

upgrade_targets:
  control_plane_target_version: "1.28"
  data_plane_target_version: "1.28"

assessment_options:
  run_cluster_insights: true
  run_kubent_scan: true
  run_pluto_scan: true
  check_deprecated_apis: true
  collect_cluster_metadata: true
```

## Generated Assessment Structure

The toolkit generates comprehensive assessment documentation in the `eks-upgrade-assessment/` folder:

```
eks-upgrade-assessment/
├── README.md                                    # Assessment overview
├── 01-pre-upgrade-assessment/
│   ├── assessment-report.md                     # Detailed assessment report
│   ├── assessment-report.html                   # Interactive HTML report
│   ├── clusters-metadata.json                   # Complete cluster metadata
│   ├── cluster-insights-findings.json          # EKS insights data
│   ├── deprecated-apis-report.md               # API deprecation analysis
│   └── compatibility-matrix.md                 # Version compatibility
├── 02-risk-analysis/
│   ├── aws-resources-inventory-{cluster}.md    # AWS resources analysis
│   ├── backup-strategy.md                      # Backup considerations
│   └── velero-limitations.md                   # Velero limitations
├── cluster-metadata/                           # Organized YAML files
│   └── {cluster-name}/
│       ├── cluster/                            # Cluster configuration
│       ├── nodegroups/                         # Node group configs
│       ├── fargate/                            # Fargate profiles
│       ├── addons/                             # EKS add-ons
│       ├── karpenter/                          # Karpenter resources
│       └── plugins/                            # AWS plugins
├── web-ui/                                     # Interactive dashboard
│   ├── package.json
│   ├── public/
│   │   ├── index.html
│   │   └── assessment-data.json
│   └── src/
│       ├── index.js
│       ├── App.js
│       └── App.css
└── scripts/
    ├── assessment-validation.sh                # Assessment validation
    ├── deprecated-api-scanner.sh               # API deprecation scanning
    └── aws-resource-inventory.sh               # AWS resource discovery
```

## Key Features

### 1. Comprehensive Assessment
- **EKS Cluster Insights**: Automated assessment of upgrade readiness
- **Deprecated API Detection**: Integration with kubent and pluto tools
- **Version Compatibility**: Validates upgrade paths and compatibility
- **Workload Analysis**: Scans for PodDisruptionBudgets and topology constraints
- **Resource Inventory**: Complete catalog of cluster resources

### 2. Cluster Metadata Collection
The toolkit collects comprehensive metadata including:

- **Cluster Configuration**: Control plane settings, networking, logging
- **Node Groups**: Managed node group configurations and status
- **Fargate Profiles**: Serverless compute configurations
- **EKS Add-ons**: Managed add-on versions and configurations
- **Karpenter Resources**: NodePools, NodeClasses, and Provisioners
- **AWS Plugins**: Third-party controllers and operators
- **Resource Relationships**: Dependencies and interconnections

### 3. Risk Analysis
- **Compatibility Issues**: Identifies potential upgrade blockers
- **Deprecated APIs**: Lists APIs that need attention before upgrade
- **Resource Dependencies**: Maps critical resource relationships
- **Version Gaps**: Analyzes version compatibility matrices
- **Backup Requirements**: Assesses backup and recovery needs

### 4. Interactive Reporting
- **HTML Dashboard**: CloudScape-based interactive interface
- **Markdown Reports**: Detailed text-based analysis
- **JSON Data**: Machine-readable assessment results
- **Visual Charts**: Resource distribution and risk visualization

### 5. Standalone Metadata Generator
Use the independent metadata generator for specific clusters:

```bash
# Generate metadata for specific cluster
python src/cluster_metadata_generator.py --region us-west-2 --profile default --clusters my-cluster --output-dir ./assessment-data/

# Generate metadata for all clusters using config file
python src/cluster_metadata_generator.py --config eks-upgrade-config.yaml --output-dir ./assessment-data/
```

## Prerequisites

- Python 3.9+
- AWS CLI configured with appropriate permissions
- kubectl (optional, for enhanced validation)
- kubent (for deprecated API scanning)
- pluto (for additional API scanning)

## Required AWS Permissions

The toolkit requires the following AWS permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "eks:ListClusters",
                "eks:DescribeCluster",
                "eks:ListNodegroups",
                "eks:DescribeNodegroup",
                "eks:ListFargateProfiles",
                "eks:DescribeFargateProfile",
                "eks:ListAddons",
                "eks:DescribeAddon",
                "eks:ListInsights",
                "eks:DescribeInsight",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
                "elbv2:DescribeLoadBalancers",
                "elbv2:DescribeTargetGroups",
                "logs:DescribeLogGroups",
                "cloudwatch:DescribeAlarms",
                "efs:DescribeFileSystems",
                "fsx:DescribeFileSystems",
                "ecr:DescribeRepositories",
                "secretsmanager:ListSecrets",
                "ssm:DescribeParameters"
            ],
            "Resource": "*"
        }
    ]
}
```

## Usage Examples

### Basic Assessment (Auto-discover all clusters)
```bash
# Initialize configuration
python src/main.py init

# Run assessment (will discover all clusters in region)
python src/main.py analyze
```

### Specific Clusters Assessment
```yaml
# Edit eks-upgrade-config.yaml
cluster_info:
  cluster_names: ["prod-cluster", "staging-cluster"]
```

### Custom Output Directory
```bash
python src/main.py analyze --output-dir my-assessment-results
```

### Standalone Metadata Collection
```bash
# Collect metadata for specific cluster
python src/cluster_metadata_generator.py --region us-west-2 --clusters my-cluster --output-dir ./cluster-data/

# Collect metadata using configuration file
python src/cluster_metadata_generator.py --config eks-upgrade-config.yaml --output-dir ./cluster-data/
```

## Assessment Best Practices

1. **Regular Assessment**: Run assessments regularly to track cluster drift
2. **Multi-Environment**: Assess all environments (dev, staging, prod) consistently
3. **Version Planning**: Plan assessments before versions reach end-of-support
4. **Documentation**: Keep assessment results for compliance and audit purposes
5. **Automation**: Integrate assessment into CI/CD pipelines for continuous monitoring

## Troubleshooting

### Common Issues

1. **AWS Credentials**: Ensure AWS credentials are properly configured
2. **Permissions**: Verify all required AWS permissions are granted
3. **Region**: Ensure the correct AWS region is specified in configuration
4. **kubectl Context**: For enhanced validation, ensure kubectl is configured for your clusters

### Assessment Tool Issues

1. **Tools Not Found**: Run `python src/main.py install-tools` to install kubent and pluto
2. **kubectl Auto-Configuration Failed**: The toolkit automatically configures kubectl for each cluster
3. **Permission Denied**: Ensure kubectl has proper RBAC permissions for cluster scanning
4. **Tool Installation Failed**: Check internet connectivity and try manual installation

### Getting Help

1. Check the generated assessment reports for detailed guidance
2. Review AWS EKS best practices documentation
3. Validate configuration using `python src/main.py validate`
4. Check AWS CloudTrail logs for permission issues
5. Verify tool installation: `kubent --version && pluto version`

## Contributing

This toolkit follows AWS EKS best practices and is designed to be extensible. Contributions are welcome for:

- Additional assessment tools integration
- Enhanced cluster metadata collection
- Improved reporting templates
- Additional validation scripts

## License

This project is provided as-is for educational and operational purposes. Please review and test thoroughly before using in production environments.