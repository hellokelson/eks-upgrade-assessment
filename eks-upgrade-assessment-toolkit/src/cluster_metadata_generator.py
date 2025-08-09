#!/usr/bin/env python3
"""
Independent Cluster Metadata Generator

This module can be used both as a standalone script and imported into other modules
to generate comprehensive EKS cluster metadata in JSON format.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import click

# Add the src directory to the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.aws_client import AWSClient
from config.parser import ConfigParser, EKSUpgradeConfig


class ClusterMetadataGenerator:
    """Independent cluster metadata generator."""
    
    def __init__(self, region: str, profile: str = "default"):
        """Initialize the metadata generator."""
        self.region = region
        self.profile = profile
        self.aws_client = AWSClient(region=region, profile=profile)
    
    def test_connection(self) -> bool:
        """Test AWS connection."""
        return self.aws_client.test_connection()
    
    def discover_clusters(self) -> List[str]:
        """Discover all EKS clusters in the region."""
        return self.aws_client.discover_clusters()
    
    def generate_cluster_metadata(self, cluster_names: Optional[List[str]] = None, 
                                output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive metadata for specified clusters or all clusters.
        
        Args:
            cluster_names: List of cluster names to analyze. If None, discovers all clusters.
            output_dir: Directory to save original YAML files. If None, no YAML files are saved.
            
        Returns:
            Dictionary containing metadata for all clusters.
        """
        if cluster_names is None:
            cluster_names = self.discover_clusters()
        
        if not cluster_names:
            raise ValueError("No clusters found or specified")
        
        all_clusters_metadata = {}
        
        for i, cluster_name in enumerate(cluster_names, 1):
            print(f"🔍 [{i}/{len(cluster_names)}] Collecting metadata for: {cluster_name}")
            
            try:
                # Collect comprehensive cluster metadata
                cluster_metadata = self.aws_client.get_cluster_metadata(cluster_name, output_dir)
                all_clusters_metadata[cluster_name] = cluster_metadata
                
                # Print summary
                print(f"✅ Metadata collected for {cluster_name}")
                print(f"   - Version: {cluster_metadata.get('cluster_version', 'N/A')}")
                print(f"   - Status: {cluster_metadata.get('cluster_status', 'N/A')}")
                print(f"   - Node Groups: {len(cluster_metadata.get('node_groups', []))}")
                print(f"   - Addons: {len(cluster_metadata.get('addons', []))}")
                print(f"   - Karpenter: {'✅' if cluster_metadata.get('karpenter', {}).get('installed') else '❌'}")
                
                # Show installed plugins
                installed_plugins = cluster_metadata.get('aws_plugins', {}).get('installed_plugins', [])
                print(f"   - AWS Plugins: {len(installed_plugins)} installed")
                
            except Exception as e:
                print(f"❌ Error collecting metadata for {cluster_name}: {str(e)}")
                all_clusters_metadata[cluster_name] = {'error': str(e)}
        
        return all_clusters_metadata
    
    def save_metadata_json(self, metadata: Dict[str, Any], output_file: str) -> None:
        """Save metadata to JSON file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        print(f"✅ Metadata saved to: {output_path}")
    
    def generate_and_save(self, cluster_names: Optional[List[str]] = None,
                         output_file: str = "clusters-metadata.json",
                         output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate cluster metadata and save to JSON file.
        
        Args:
            cluster_names: List of cluster names to analyze. If None, discovers all clusters.
            output_file: Path to save the JSON metadata file.
            output_dir: Directory to save original YAML files. If None, no YAML files are saved.
            
        Returns:
            Dictionary containing metadata for all clusters.
        """
        print(f"🚀 Starting cluster metadata generation...")
        print(f"📍 Region: {self.region}")
        print(f"👤 Profile: {self.profile}")
        
        # Test connection
        if not self.test_connection():
            raise ConnectionError("Failed to connect to AWS. Check credentials and permissions.")
        
        print("✅ AWS connection successful")
        
        # Generate metadata
        metadata = self.generate_cluster_metadata(cluster_names, output_dir)
        
        # Ensure output_file is in cluster-metadata directory if output_dir is specified
        if output_dir and not output_file.startswith(output_dir):
            cluster_metadata_dir = os.path.join(output_dir, "cluster-metadata")
            output_file = os.path.join(cluster_metadata_dir, os.path.basename(output_file))
        
        # Save to file
        self.save_metadata_json(metadata, output_file)
        
        print(f"\n📊 Summary:")
        print(f"   - Total clusters: {len(metadata)}")
        print(f"   - Successful: {len([m for m in metadata.values() if 'error' not in m])}")
        print(f"   - Errors: {len([m for m in metadata.values() if 'error' in m])}")
        
        return metadata


def load_config_and_generate(config_file: str = "eks-upgrade-config.yaml",
                           output_file: str = "clusters-metadata.json",
                           output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file and generate metadata.
    
    Args:
        config_file: Path to the EKS upgrade configuration file.
        output_file: Path to save the JSON metadata file.
        output_dir: Directory to save original YAML files.
        
    Returns:
        Dictionary containing metadata for all clusters.
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    # Load configuration
    upgrade_config = ConfigParser.load_config(config_file)
    
    # Initialize generator
    generator = ClusterMetadataGenerator(
        region=upgrade_config.aws_configuration.region,
        profile=upgrade_config.aws_configuration.credentials_profile
    )
    
    # Get cluster names from config or discover all
    cluster_names = upgrade_config.cluster_info.cluster_names
    if not cluster_names:
        cluster_names = None  # Will discover all clusters
    
    # Generate and save metadata
    return generator.generate_and_save(cluster_names, output_file, output_dir)


# CLI interface for standalone usage
@click.command()
@click.option('--config', '-c', default='eks-upgrade-config.yaml',
              help='Path to EKS upgrade configuration file')
@click.option('--output', '-o', default='clusters-metadata.json',
              help='Output path for JSON metadata file')
@click.option('--output-dir', '-d', default=None,
              help='Directory to save original YAML files (optional)')
@click.option('--region', '-r', default=None,
              help='AWS region (overrides config file)')
@click.option('--profile', '-p', default=None,
              help='AWS profile (overrides config file)')
@click.option('--clusters', '-cl', multiple=True,
              help='Specific cluster names to analyze (can be used multiple times)')
def main(config: str, output: str, output_dir: Optional[str], 
         region: Optional[str], profile: Optional[str], clusters: tuple):
    """Generate EKS cluster metadata JSON file."""
    try:
        if region and profile:
            # Use command line parameters
            generator = ClusterMetadataGenerator(region=region, profile=profile)
            cluster_names = list(clusters) if clusters else None
            generator.generate_and_save(cluster_names, output, output_dir)
        else:
            # Use configuration file
            load_config_and_generate(config, output, output_dir)
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()