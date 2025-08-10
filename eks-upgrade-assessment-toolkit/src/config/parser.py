"""Configuration parser for EKS upgrade toolkit."""

import yaml
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class AWSConfiguration:
    """AWS configuration settings."""
    region: str = "us-west-2"
    credentials_profile: str = "default"


@dataclass
class ClusterInfo:
    """EKS cluster information."""
    cluster_names: List[str] = field(default_factory=list)
    current_control_plane_version: Optional[str] = None
    current_data_plane_version: Optional[str] = None


@dataclass
class UpgradeTargets:
    """Upgrade target versions."""
    control_plane_target_version: str = "1.28"
    data_plane_target_version: str = "1.28"


@dataclass
class UpgradeStrategy:
    """Upgrade strategy configuration."""
    method: str = "both"  # "in-place", "blue-green", or "both"


@dataclass
class ResilienceRequirements:
    """Resilience and backup requirements."""
    enable_resilience_hub: bool = True
    backup_strategy: str = "velero"


@dataclass
class AssessmentOptions:
    """Assessment tool options."""
    run_cluster_insights: bool = True
    run_kubent_scan: bool = True
    run_pluto_scan: bool = True
    check_deprecated_apis: bool = True
    run_addon_compatibility_analysis: bool = True
    collect_cluster_metadata: bool = True


@dataclass
class EKSUpgradeConfig:
    """Main configuration class for EKS upgrade toolkit."""
    aws_configuration: AWSConfiguration = field(default_factory=AWSConfiguration)
    cluster_info: ClusterInfo = field(default_factory=ClusterInfo)
    upgrade_targets: UpgradeTargets = field(default_factory=UpgradeTargets)
    upgrade_strategy: UpgradeStrategy = field(default_factory=UpgradeStrategy)
    resilience_requirements: ResilienceRequirements = field(default_factory=ResilienceRequirements)
    assessment_options: AssessmentOptions = field(default_factory=AssessmentOptions)


class ConfigParser:
    """Parser for EKS upgrade configuration files."""
    
    @staticmethod
    def load_config(config_path: str) -> EKSUpgradeConfig:
        """Load configuration from YAML file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as file:
            config_data = yaml.safe_load(file)
        
        return ConfigParser._parse_config(config_data)
    
    @staticmethod
    def _parse_config(config_data: Dict[str, Any]) -> EKSUpgradeConfig:
        """Parse configuration data into EKSUpgradeConfig object."""
        config = EKSUpgradeConfig()
        
        # Parse AWS configuration
        if 'aws_configuration' in config_data:
            aws_config = config_data['aws_configuration']
            config.aws_configuration = AWSConfiguration(
                region=aws_config.get('region', 'us-west-2'),
                credentials_profile=aws_config.get('credentials_profile', 'default')
            )
        
        # Parse cluster info
        if 'cluster_info' in config_data:
            cluster_config = config_data['cluster_info']
            config.cluster_info = ClusterInfo(
                cluster_names=cluster_config.get('cluster_names', []),
                current_control_plane_version=cluster_config.get('current_control_plane_version'),
                current_data_plane_version=cluster_config.get('current_data_plane_version')
            )
        
        # Parse upgrade targets
        if 'upgrade_targets' in config_data:
            targets_config = config_data['upgrade_targets']
            config.upgrade_targets = UpgradeTargets(
                control_plane_target_version=targets_config.get('control_plane_target_version', '1.28'),
                data_plane_target_version=targets_config.get('data_plane_target_version', '1.28')
            )
        
        # Parse upgrade strategy
        if 'upgrade_strategy' in config_data:
            strategy_config = config_data['upgrade_strategy']
            config.upgrade_strategy = UpgradeStrategy(
                method=strategy_config.get('method', 'both')
            )
        
        # Parse resilience requirements
        if 'resilience_requirements' in config_data:
            resilience_config = config_data['resilience_requirements']
            config.resilience_requirements = ResilienceRequirements(
                enable_resilience_hub=resilience_config.get('enable_resilience_hub', True),
                backup_strategy=resilience_config.get('backup_strategy', 'velero')
            )
        
        # Parse assessment options
        if 'assessment_options' in config_data:
            assessment_config = config_data['assessment_options']
            config.assessment_options = AssessmentOptions(
                run_cluster_insights=assessment_config.get('run_cluster_insights', True),
                run_kubent_scan=assessment_config.get('run_kubent_scan', True),
                run_pluto_scan=assessment_config.get('run_pluto_scan', True),
                check_deprecated_apis=assessment_config.get('check_deprecated_apis', True),
                run_addon_compatibility_analysis=assessment_config.get('run_addon_compatibility_analysis', True),
                collect_cluster_metadata=assessment_config.get('collect_cluster_metadata', True)
            )
        
        return config
    
    @staticmethod
    def validate_config(config: EKSUpgradeConfig) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate upgrade strategy method
        valid_methods = ['in-place', 'blue-green', 'both']
        if config.upgrade_strategy.method not in valid_methods:
            errors.append(f"Invalid upgrade method: {config.upgrade_strategy.method}. Must be one of: {valid_methods}")
        
        # Validate backup strategy
        valid_backup_strategies = ['velero', 'none']
        if config.resilience_requirements.backup_strategy not in valid_backup_strategies:
            errors.append(f"Invalid backup strategy: {config.resilience_requirements.backup_strategy}. Must be one of: {valid_backup_strategies}")
        
        # Validate AWS region format (basic check)
        if not config.aws_configuration.region or len(config.aws_configuration.region.split('-')) < 3:
            errors.append(f"Invalid AWS region format: {config.aws_configuration.region}")
        
        return errors
    
    @staticmethod
    def create_sample_config(output_path: str) -> None:
        """Create a sample configuration file."""
        sample_config = {
            'aws_configuration': {
                'region': 'us-west-2',
                'credentials_profile': 'default'
            },
            'cluster_info': {
                'cluster_names': [],  # Empty list will discover all clusters
                'current_control_plane_version': None,  # Will be auto-detected
                'current_data_plane_version': None  # Will be auto-detected
            },
            'upgrade_targets': {
                'control_plane_target_version': '1.28',
                'data_plane_target_version': '1.28'
            },
            'upgrade_strategy': {
                'method': 'both'  # Options: "in-place", "blue-green", or "both"
            },
            'resilience_requirements': {
                'enable_resilience_hub': True,
                'backup_strategy': 'velero'
            },
            'assessment_options': {
                'run_cluster_insights': True,
                'run_kubent_scan': True,
                'run_pluto_scan': True,
                'check_deprecated_apis': True,
                'run_addon_compatibility_analysis': True,
                'collect_cluster_metadata': True
            }
        }
        
        with open(output_path, 'w') as file:
            yaml.dump(sample_config, file, default_flow_style=False, indent=2)