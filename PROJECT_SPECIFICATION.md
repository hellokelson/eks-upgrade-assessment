# EKS Upgrade Assessment Toolkit - Project Specification

## Project Overview
A focused toolkit to assess EKS cluster readiness for upgrades following AWS best practices. The system generates comprehensive assessment reports and provides analysis tools to identify potential issues before upgrade execution.

## Project Goals
1. **Automated Assessment**: Analyze current EKS cluster readiness for upgrade
2. **Risk Identification**: Identify potential issues and compatibility problems
3. **Comprehensive Reporting**: Generate detailed assessment reports in multiple formats
4. **Cluster Metadata Collection**: Collect and organize all cluster configuration data
5. **Deprecated API Detection**: Identify deprecated APIs that need attention

## User Input Requirements
The system accepts a configuration file with assessment parameters:

```yaml
# eks-upgrade-config.yaml
aws_configuration:
  region: "us-west-2"
  credentials_profile: "default"
  
cluster_info:
  cluster_names: []  # If empty, will discover all EKS clusters in the region
  # cluster_names: ["cluster-1", "cluster-2"]  # Or specify specific clusters
  current_control_plane_version: "1.27"  # Optional: will be auto-detected if not specified
  current_data_plane_version: "1.27"     # Optional: will be auto-detected if not specified
  
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

## System Output Structure
The system generates a structured assessment folder: `eks-upgrade-assessment/`

```
eks-upgrade-assessment/
├── README.md                           # Assessment overview and summary
├── assessment-reports/
│   ├── assessment-report.md            # Detailed markdown report
│   ├── clusters-metadata.json          # Complete cluster metadata
│   ├── cluster-insights-findings.json  # EKS insights results
│   ├── deprecated-apis-report.md       # API deprecation analysis
│   ├── compatibility-matrix.md         # Version compatibility analysis
│   └── web-ui/                         # Interactive web dashboard
│       ├── index.html                  # Main assessment dashboard
│       ├── assessment-data.json        # Generated from assessment data
│       ├── package.json               # Dependencies (optional)
│       └── assets/                     # CSS, JS, and other assets
├── cluster-metadata/                   # Organized YAML files by cluster
│   └── {cluster-name}/
│       ├── cluster/
│       │   └── cluster.yaml
│       ├── nodegroups/
│       │   └── nodegroup-{name}.yaml
│       ├── fargate/
│       │   └── fargate-{name}.yaml
│       ├── addons/
│       │   └── addon-{name}.yaml
│       ├── karpenter/
│       │   ├── karpenter-nodepools.yaml
│       │   ├── karpenter-nodeclasses.yaml
│       │   └── karpenter-provisioners.yaml
│       └── plugins/
│           └── {plugin-configs}.yaml
└── scripts/
    ├── assessment-checks.sh            # Assessment validation scripts
    ├── deprecated-api-scanner.sh       # API deprecation scanner
    └── cluster-metadata-collector.sh   # Metadata collection script
```

## Core Components

### 1. Configuration Parser
- Reads and validates assessment configuration
- Sets default values for optional parameters
- Validates AWS credentials and cluster access
- **Cluster Discovery**: Automatically discovers all EKS clusters if none specified
- **Version Auto-detection**: Detects current versions if not specified

### 2. Cluster Assessment Engine
- **Cluster Insights Integration**: Runs EKS insights analysis
- **Deprecated API Scanner**: Integrates kubent and pluto tools
- **Compatibility Checker**: Validates version compatibility
- **Workload Analysis**: Analyzes PodDisruptionBudgets, topology constraints
- **Resource Inventory**: Catalogs all cluster resources

### 3. Metadata Collection Engine
- **Comprehensive Collection**: Gathers all cluster configuration data
- **Organized Storage**: Saves data in categorized YAML files
- **JSON Export**: Creates lightweight JSON metadata for analysis
- **Resource Relationships**: Maps dependencies between resources

### 4. Assessment Report Generator
- **Multi-format Output**: Generates markdown and HTML reports
- **Interactive Dashboard**: CloudScape web interface
- **Risk Analysis**: Identifies and categorizes potential issues
- **Recommendations**: Provides actionable remediation steps

### 5. Script Generator
- **Assessment Scripts**: Automated validation and checking tools
- **API Scanner**: Custom deprecated API detection scripts
- **Metadata Collector**: Cluster data collection automation

## Implementation Architecture

### Technology Stack
- **Backend**: Python 3.9+
- **CLI Framework**: Click
- **Template Engine**: Jinja2
- **AWS SDK**: boto3
- **Kubernetes Client**: kubernetes-python-client
- **Documentation Format**: Markdown + HTML
- **Configuration Format**: YAML

### Project Structure
```
eks-upgrade-assessment-toolkit/
├── src/
│   ├── __init__.py
│   ├── main.py                         # CLI entry point
│   ├── cluster_metadata_generator.py   # Standalone metadata generator
│   ├── config/
│   │   ├── __init__.py
│   │   └── parser.py                   # Configuration parsing
│   ├── assessment/
│   │   ├── __init__.py
│   │   ├── cluster_insights.py         # EKS Cluster Insights
│   │   ├── deprecated_apis.py          # kubent/pluto integration
│   │   ├── compatibility.py            # Version compatibility checks
│   │   └── workload_analyzer.py        # Workload analysis
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── reports.py                  # Report generation
│   │   ├── scripts.py                  # Script generation
│   │   └── templates/                  # Jinja2 templates
│   └── utils/
│       ├── __init__.py
│       ├── aws_client.py               # AWS SDK wrapper
│       └── resource_inventory.py       # Resource cataloging
├── templates/
│   ├── assessment-report.md.j2
│   ├── assessment-report.html.j2
│   └── scripts/
│       └── assessment-checks.sh.j2
├── tests/
├── requirements.txt
├── install-tools.sh
└── README.md
```

## Key Features

### 1. Comprehensive Assessment
- **Multi-tool Integration**: kubent, pluto, EKS insights
- **Version Compatibility**: Control plane and data plane analysis
- **Resource Analysis**: Complete cluster resource inventory
- **Risk Scoring**: Categorized risk assessment

### 2. Metadata Collection
- **Complete Coverage**: All cluster configurations and resources
- **Organized Structure**: Categorized by resource type
- **Multiple Formats**: YAML originals + JSON summary
- **Standalone Module**: Independent metadata generator

### 3. Interactive Reporting
- **HTML Dashboard**: CloudScape-based web interface
- **Markdown Reports**: Detailed text-based analysis
- **JSON Data**: Machine-readable assessment results
- **Visual Charts**: Resource distribution and risk analysis

### 4. Automation Tools
- **Assessment Scripts**: Automated validation tools
- **Collection Scripts**: Metadata gathering automation
- **Scanner Integration**: Deprecated API detection

## Success Criteria
1. **Accuracy**: Comprehensive and accurate cluster assessment
2. **Completeness**: Covers all upgrade-relevant aspects
3. **Usability**: Clear, actionable assessment results
4. **Automation**: Minimal manual intervention required
5. **Reliability**: Robust error handling and validation

## Risk Mitigation
1. **API Changes**: Version-pinned tool dependencies
2. **Cluster Access**: Comprehensive permission validation
3. **Tool Dependencies**: Graceful degradation when tools unavailable
4. **Data Quality**: Extensive validation and error handling
5. **Performance**: Optimized for large multi-cluster environments

This specification focuses the toolkit on assessment and analysis, providing the foundation for informed upgrade planning decisions.