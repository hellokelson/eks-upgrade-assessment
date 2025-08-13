#!/usr/bin/env python3
"""
EKS Upgrade Assessment Toolkit - Main CLI Entry Point

A comprehensive toolkit to assess EKS cluster readiness for upgrades 
following AWS best practices.
"""

import click
import os
import sys
from typing import Optional
from pathlib import Path

import subprocess
import json
from typing import Dict, Any

from config.parser import ConfigParser, EKSUpgradeConfig
from utils.aws_client import AWSClient
from utils.resource_inventory import ResourceInventoryGenerator
from cluster_metadata_generator import ClusterMetadataGenerator


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """EKS Upgrade Assessment Toolkit
    
    A comprehensive toolkit to assess EKS cluster readiness for upgrades 
    following AWS best practices.
    """
    pass


@cli.command()
@click.option('--output', '-o', default='eks-upgrade-config.yaml', 
              help='Output path for sample configuration file')
def init(output: str):
    """Initialize a new EKS upgrade configuration file."""
    try:
        if os.path.exists(output):
            if not click.confirm(f"Configuration file {output} already exists. Overwrite?"):
                click.echo("Operation cancelled.")
                return
        
        ConfigParser.create_sample_config(output)
        click.echo(f"✅ Sample configuration created: {output}")
        click.echo("\nNext steps:")
        click.echo(f"1. Edit {output} to match your environment")
        click.echo("2. Run 'python main.py analyze' to start the assessment")
        
    except Exception as e:
        click.echo(f"❌ Error creating configuration: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def install_tools():
    """Install required assessment tools (kubent and pluto)."""
    try:
        click.echo("🔧 Installing EKS upgrade assessment tools...")
        
        # Check if install script exists
        install_script = Path("install-tools.sh")
        if not install_script.exists():
            click.echo("❌ Installation script not found: install-tools.sh", err=True)
            click.echo("Please ensure you're running from the toolkit root directory.", err=True)
            sys.exit(1)
        
        # Run installation script
        result = subprocess.run(["bash", str(install_script)], check=False)
        
        if result.returncode == 0:
            click.echo("✅ Tools installation completed successfully!")
            click.echo("\nNext steps:")
            click.echo("1. Restart your terminal or run: source ~/.bashrc")
            click.echo("2. Verify tools: kubent --version && pluto version")
            click.echo("3. Configure kubectl for your EKS clusters")
            click.echo("4. Run assessment: python src/main.py analyze")
        else:
            click.echo("❌ Tools installation failed. Check the output above for details.", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error during tools installation: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='eks-upgrade-config.yaml', help='Configuration file path')
@click.option('--region', '-r', help='AWS region (overrides config)')
@click.option('--force-refresh', '-f', is_flag=True, help='Force refresh of addon data even if cached')
def prepare(config: str, region: str, force_refresh: bool):
    """Prepare common EKS addon version data for analysis."""
    try:
        click.echo("🔧 Preparing EKS addon version data...")
        
        # Load configuration to get region if not provided
        if not region:
            if not os.path.exists(config):
                click.echo(f"❌ Configuration file not found: {config}", err=True)
                click.echo("Run 'python main.py init' to create a sample configuration.")
                sys.exit(1)
            
            upgrade_config = ConfigParser.load_config(config)
            region = upgrade_config.aws_configuration.region
        
        click.echo(f"📍 Using AWS region: {region}")
        
        # Prepare addon version data in shared location
        from addon_version_fetcher import EKSAddonVersionFetcher
        
        # Use a standard shared data location
        shared_data_dir = Path("assessment-reports/shared-data")
        shared_data_dir.mkdir(parents=True, exist_ok=True)
        
        fetcher = EKSAddonVersionFetcher(region=region)
        
        # Check if data exists and is recent (unless force refresh)
        addon_versions_file = shared_data_dir / "eks-addon-versions.json"
        
        if addon_versions_file.exists() and not force_refresh:
            click.echo("✅ EKS addon version data already exists")
            click.echo(f"📁 Location: {addon_versions_file}")
            click.echo("💡 Use --force-refresh to update the data")
            
            # Show data summary
            try:
                import json
                with open(addon_versions_file, 'r') as f:
                    data = json.load(f)
                metadata = data.get('metadata', {})
                click.echo(f"📊 Data summary:")
                click.echo(f"   - EKS versions: {len(metadata.get('eks_versions', []))}")
                click.echo(f"   - Total addons: {metadata.get('total_addons', 0)}")
                click.echo(f"   - Region: {metadata.get('region', 'unknown')}")
            except Exception:
                pass
        else:
            # Fetch fresh data
            click.echo("🔍 Fetching comprehensive EKS addon version compatibility data...")
            addon_versions_data = fetcher.fetch_all_addon_versions()
            
            # Save to shared location
            import json
            with open(addon_versions_file, 'w') as f:
                json.dump(addon_versions_data, f, indent=2, default=str)
            
            click.echo(f"✅ EKS addon version data prepared successfully!")
            click.echo(f"📁 Saved to: {addon_versions_file}")
            
            metadata = addon_versions_data.get('metadata', {})
            click.echo(f"📊 Data summary:")
            click.echo(f"   - EKS versions: {len(metadata.get('eks_versions', []))}")
            click.echo(f"   - Total addons: {metadata.get('total_addons', 0)}")
            click.echo(f"   - Region: {metadata.get('region', 'unknown')}")
        
        # Generate EKS addon IAM policy mapping
        click.echo("🔐 Generating EKS addon IAM policy mapping...")
        from eks_addon_iam_policies import save_addon_iam_mapping
        
        iam_mapping_file = save_addon_iam_mapping(Path("assessment-reports"))
        click.echo(f"✅ EKS addon IAM policy mapping saved to: {iam_mapping_file}")
        
        # Show IAM mapping summary
        from eks_addon_iam_policies import load_addon_iam_mapping
        iam_data = load_addon_iam_mapping(Path("assessment-reports/shared-data"))
        iam_summary = iam_data.get('summary', {})
        click.echo(f"📊 IAM mapping summary:")
        click.echo(f"   - Total addons: {iam_summary.get('total_addons', 0)}")
        click.echo(f"   - Require IAM: {iam_summary.get('require_iam', 0)}")
        click.echo(f"   - No IAM required: {iam_summary.get('no_iam_required', 0)}")
        
        click.echo("\n🎯 Next steps:")
        click.echo("   1. Run 'python src/main.py analyze' to analyze clusters")
        click.echo("   2. The analysis will use the prepared addon data automatically")
        click.echo("   3. No need to fetch addon data during cluster analysis")
        
    except Exception as e:
        click.echo(f"❌ Error preparing addon data: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='eks-upgrade-config.yaml',
              help='Path to configuration file')
@click.option('--output-dir', '-o', default='eks-upgrade-assessment',
              help='Output directory for generated assessment reports (default: assessment-reports/{account_id}-{region}-{datetime}-assessment)')
def analyze(config: str, output_dir: str):
    """Analyze EKS clusters and generate assessment reports."""
    try:
        # Load and validate configuration
        click.echo("🔍 Loading configuration...")
        if not os.path.exists(config):
            click.echo(f"❌ Configuration file not found: {config}", err=True)
            click.echo("Run 'python main.py init' to create a sample configuration.")
            sys.exit(1)
        
        upgrade_config = ConfigParser.load_config(config)
        
        # Validate configuration
        errors = ConfigParser.validate_config(upgrade_config)
        if errors:
            click.echo("❌ Configuration validation failed:", err=True)
            for error in errors:
                click.echo(f"  - {error}", err=True)
            sys.exit(1)
        
        click.echo("✅ Configuration loaded successfully")
        
        # Initialize AWS client
        click.echo("🔗 Connecting to AWS...")
        aws_client = AWSClient(
            region=upgrade_config.aws_configuration.region,
            profile=upgrade_config.aws_configuration.credentials_profile
        )
        
        if not aws_client.test_connection():
            click.echo("❌ Failed to connect to AWS. Please check your credentials and permissions.", err=True)
            sys.exit(1)
        
        click.echo("✅ AWS connection successful")
        
        # Generate dynamic output directory name: assessment-reports/{account_id}-{region}-{datetime}-assessment
        try:
            if output_dir == 'eks-upgrade-assessment':  # Only change if using default
                account_id = aws_client.get_account_id()
                region = upgrade_config.aws_configuration.region
                
                # Generate timestamp for directory name
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                
                # Create dynamic output directory name inside assessment-reports
                dynamic_dir_name = f"{account_id}-{region}-{timestamp}-assessment"
                dynamic_output_dir = f"assessment-reports/{dynamic_dir_name}"
                click.echo(f"📁 Using dynamic output directory: {dynamic_output_dir}")
                output_dir = dynamic_output_dir
            else:
                click.echo(f"📁 Using specified output directory: {output_dir}")
                
        except Exception as e:
            click.echo(f"⚠️  Could not get AWS account info for dynamic naming: {str(e)}")
            click.echo(f"📁 Using default output directory: {output_dir}")
        
        # Discover clusters if not specified
        cluster_names = upgrade_config.cluster_info.cluster_names
        if not cluster_names:
            click.echo("🔍 Discovering EKS clusters...")
            cluster_names = aws_client.discover_clusters()
            if not cluster_names:
                click.echo("❌ No EKS clusters found in the region.", err=True)
                sys.exit(1)
            click.echo(f"✅ Found {len(cluster_names)} clusters: {', '.join(cluster_names)}")
        
        # Initialize resource inventory generator
        inventory_generator = ResourceInventoryGenerator(aws_client)
        
        # Step 1: Load pre-prepared addon version data
        click.echo("🔧 Loading pre-prepared EKS addon version data...")
        
        # Check for pre-prepared addon data in standard shared location
        shared_addon_file = Path("assessment-reports/shared-data/eks-addon-versions.json")
        
        if shared_addon_file.exists():
            try:
                with open(shared_addon_file, 'r') as f:
                    addon_versions_data = json.load(f)
                click.echo("✅ Using pre-prepared EKS addon version data")
                
                # Show data summary
                metadata = addon_versions_data.get('metadata', {})
                click.echo(f"📊 Addon data summary: {len(metadata.get('eks_versions', []))} EKS versions, {metadata.get('total_addons', 0)} addons")
            except Exception as e:
                click.echo(f"⚠️  Warning: Could not load pre-prepared addon data: {e}")
                addon_versions_data = None
        else:
            click.echo("⚠️  No pre-prepared addon data found")
            click.echo("💡 Run 'python src/main.py prepare' first to prepare addon data")
            click.echo("🔄 Falling back to on-demand addon data fetching...")
            
            # Fallback to on-demand fetching
            from addon_version_fetcher import fetch_and_cache_addon_versions
            addon_versions_file = fetch_and_cache_addon_versions(
                region=upgrade_config.aws_configuration.region,
                output_dir=output_dir,
                force_refresh=False
            )
            
            from addon_version_fetcher import EKSAddonVersionFetcher
            addon_versions_data = EKSAddonVersionFetcher.load_addon_versions_data(output_dir)
        
        # Analyze clusters with pre-prepared addon data
        click.echo(f"📊 Analyzing {len(cluster_names)} clusters...")
        cluster_analysis = {}
        
        # Determine timeout strategy based on cluster count
        if len(cluster_names) > 10:
            click.echo(f"⚡ Large cluster count detected ({len(cluster_names)}). Using optimized scanning...")
            kubent_timeout = 5  # Shorter timeout for many clusters
            skip_slow_scans = True
        else:
            kubent_timeout = 10  # Normal timeout for few clusters
            skip_slow_scans = False
        
        for i, cluster_name in enumerate(cluster_names, 1):
            click.echo(f"  [{i}/{len(cluster_names)}] Analyzing cluster: {cluster_name}")
            
            # Auto-configure kubectl for this cluster
            if upgrade_config.assessment_options.run_kubent_scan or upgrade_config.assessment_options.run_pluto_scan:
                click.echo(f"    🔧 Configuring kubectl for cluster access...")
                kubectl_config = configure_kubectl_for_cluster(cluster_name, upgrade_config.aws_configuration.region)
                if kubectl_config['status'] != 'success':
                    click.echo(f"    ⚠️  kubectl configuration failed: {kubectl_config.get('error', 'Unknown error')}")
                    click.echo(f"    ⚠️  kubent/pluto scans may fail for this cluster")
                else:
                    click.echo(f"    ✅ kubectl configured successfully")
            
            # Get cluster information
            cluster_info = aws_client.get_cluster_info(cluster_name)
            if not cluster_info:
                click.echo(f"    ⚠️  Failed to get cluster info for {cluster_name}")
                continue
            
            # Get node groups
            node_groups = aws_client.get_node_groups(cluster_name)
            
            # Get cluster insights
            insights = []
            if upgrade_config.assessment_options.run_cluster_insights:
                click.echo(f"    🔍 Running cluster insights...")
                insights = aws_client.get_cluster_insights(cluster_name)
            
            # Run kubent scan if configured (with adaptive timeout)
            kubent_results = {}
            if upgrade_config.assessment_options.run_kubent_scan:
                if skip_slow_scans:
                    click.echo(f"    🔧 Running kubent scan (fast mode)...")
                    kubent_results = run_kubent_scan_fast(cluster_name, kubent_timeout)
                else:
                    click.echo(f"    🔧 Running kubent scan...")
                    kubent_results = run_kubent_scan(cluster_name)
            
            # Run pluto scan if configured (skip for large cluster counts)
            pluto_results = {}
            if upgrade_config.assessment_options.run_pluto_scan and not skip_slow_scans:
                click.echo(f"    🔧 Running pluto scan...")
                pluto_results = run_pluto_scan(cluster_name)
            elif skip_slow_scans:
                pluto_results = {
                    'status': 'skipped',
                    'deprecated_apis': [],
                    'error': 'Skipped for large cluster count - run manually if needed'
                }
            
            # Check deprecated APIs if configured
            deprecated_api_results = {}
            if upgrade_config.assessment_options.check_deprecated_apis:
                click.echo(f"    📊 Checking deprecated APIs...")
                deprecated_api_results = check_deprecated_apis(aws_client, cluster_name)
            
            # Get addons
            addons = aws_client.get_addons(cluster_name)
            
            # Get Fargate profiles
            fargate_profiles = aws_client.get_fargate_profiles(cluster_name)
            
            # Generate AWS resource inventory
            click.echo(f"    📋 Generating AWS resource inventory...")
            resource_inventory = inventory_generator.generate_inventory(cluster_name)
            
            # Collect comprehensive cluster metadata
            click.echo(f"    🔍 Collecting comprehensive cluster metadata...")
            try:
                cluster_metadata = aws_client.get_cluster_metadata(cluster_name, output_dir)
                click.echo(f"    ✅ Cluster metadata collected successfully")
            except Exception as e:
                click.echo(f"    ❌ Error collecting cluster metadata: {str(e)}")
                cluster_metadata = {}
            
            # Run addon compatibility analysis for target version
            addon_compatibility_results = {}
            if upgrade_config.assessment_options.run_addon_compatibility_analysis and addon_versions_data:
                try:
                    from cluster_addon_analyzer import analyze_cluster_addons
                    
                    # Get current addons from cluster metadata or addons list
                    current_addons = []
                    if cluster_metadata and 'addons' in cluster_metadata:
                        current_addons = cluster_metadata['addons']
                    elif addons:
                        current_addons = addons
                    
                    if current_addons:
                        addon_compatibility_results = analyze_cluster_addons(
                            cluster_name=cluster_name,
                            current_eks_version=cluster_info.version,
                            target_eks_version=upgrade_config.upgrade_targets.control_plane_target_version,
                            current_addons=current_addons,
                            addon_versions_data=addon_versions_data
                        )
                    else:
                        addon_compatibility_results = {
                            'status': 'no_addons', 
                            'message': 'No addons found for analysis',
                            'summary': {'total_addons': 0, 'pass': 0, 'error': 0, 'warning': 0, 'unknown': 0}
                        }
                except Exception as e:
                    click.echo(f"    ⚠️  Warning: Addon compatibility analysis failed: {str(e)}")
                    addon_compatibility_results = {
                        'status': 'error', 
                        'error': str(e),
                        'summary': {'total_addons': 0, 'pass': 0, 'error': 0, 'warning': 0, 'unknown': 0}
                    }
            elif not upgrade_config.assessment_options.run_addon_compatibility_analysis:
                addon_compatibility_results = {
                    'status': 'disabled',
                    'message': 'Addon compatibility analysis disabled in configuration',
                    'summary': {'total_addons': 0, 'pass': 0, 'error': 0, 'warning': 0, 'unknown': 0}
                }
            else:
                addon_compatibility_results = {
                    'status': 'no_data',
                    'message': 'Addon version data not available',
                    'summary': {'total_addons': 0, 'pass': 0, 'error': 0, 'warning': 0, 'unknown': 0}
                }
            
            # Run addon IAM role and policy analysis
            addon_iam_results = {}
            try:
                from addon_iam_analyzer import analyze_cluster_addon_iam_roles
                
                # Get current addons from cluster metadata or addons list
                current_addons = []
                if cluster_metadata and 'addons' in cluster_metadata:
                    current_addons = cluster_metadata['addons']
                elif addons:
                    current_addons = addons
                
                if current_addons:
                    addon_iam_results = analyze_cluster_addon_iam_roles(
                        cluster_name=cluster_name,
                        addons=current_addons,
                        aws_client=aws_client,
                        shared_data_dir=Path("assessment-reports/shared-data")
                    )
                else:
                    addon_iam_results = {
                        'cluster_name': cluster_name,
                        'addon_iam_analysis': [],
                        'summary': {'total_addons': 0, 'pass': 0, 'warning': 0, 'error': 0, 'not_applicable': 0},
                        'recommendations': ['No addons found for IAM analysis']
                    }
                    
            except Exception as e:
                click.echo(f"    ⚠️  Warning: Addon IAM analysis failed: {str(e)}")
                addon_iam_results = {
                    'cluster_name': cluster_name,
                    'addon_iam_analysis': [],
                    'summary': {'total_addons': 0, 'pass': 0, 'warning': 0, 'error': 0, 'not_applicable': 0},
                    'recommendations': [f'IAM analysis failed: {str(e)}'],
                    'error': str(e)
                }
            
            cluster_analysis[cluster_name] = {
                'cluster_info': cluster_info,
                'node_groups': node_groups,
                'insights': insights,
                'kubent_results': kubent_results,
                'pluto_results': pluto_results,
                'deprecated_api_results': deprecated_api_results,
                'addons': addons,
                'fargate_profiles': fargate_profiles,
                'resource_inventory': resource_inventory,
                'cluster_metadata': cluster_metadata,
                'addon_compatibility': addon_compatibility_results,
                'addon_iam_analysis': addon_iam_results
            }
            
            click.echo(f"    ✅ Analysis complete for {cluster_name}")
        
        if skip_slow_scans:
            click.echo("⚡ Fast mode was used for large cluster count. Some scans were skipped.")
            click.echo("   Run individual cluster analysis for detailed kubent/pluto results if needed.")
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate documentation
        click.echo("📝 Generating assessment reports...")
        generate_documentation(upgrade_config, cluster_analysis, output_dir)
        
        click.echo(f"✅ Assessment reports generated successfully in: {output_dir}")
        click.echo("\nNext steps:")
        click.echo(f"1. Review the generated assessment reports in {output_dir}")
        click.echo("2. Open the web dashboard for interactive viewing:")
        click.echo(f"   - Web Dashboard: {output_dir}/web-ui/index.html")
        click.echo(f"   - Assessment Data: {output_dir}/clusters-metadata.json")
        click.echo("3. Analyze the risk assessment and compatibility findings")
        click.echo("4. Plan your upgrade strategy based on the assessment results")
        
    except Exception as e:
        click.echo(f"❌ Error during analysis: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', default='eks-upgrade-config.yaml',
              help='Path to configuration file')
def validate(config: str):
    """Validate configuration file."""
    try:
        if not os.path.exists(config):
            click.echo(f"❌ Configuration file not found: {config}", err=True)
            sys.exit(1)
        
        upgrade_config = ConfigParser.load_config(config)
        errors = ConfigParser.validate_config(upgrade_config)
        
        if errors:
            click.echo("❌ Configuration validation failed:", err=True)
            for error in errors:
                click.echo(f"  - {error}", err=True)
            sys.exit(1)
        else:
            click.echo("✅ Configuration is valid")
            
    except Exception as e:
        click.echo(f"❌ Error validating configuration: {str(e)}", err=True)
        sys.exit(1)


def determine_insights_status(insights):
    """Determine the overall status based on individual insight statuses."""
    if not insights:
        return 'no_data'
    
    # Check for ERROR status (highest priority)
    if any(insight.get('insightStatus', {}).get('status') == 'ERROR' for insight in insights):
        return 'error'
    
    # Check for WARNING status (medium priority)
    if any(insight.get('insightStatus', {}).get('status') == 'WARNING' for insight in insights):
        return 'warning'
    
    # If all are PASSING or other non-critical statuses
    return 'success'


def configure_kubectl_for_cluster(cluster_name: str, region: str) -> Dict[str, Any]:
    """Automatically configure kubectl for the specified cluster."""
    result = {
        'status': 'not_configured',
        'error': None
    }
    
    try:
        # Run aws eks update-kubeconfig command
        cmd = ['aws', 'eks', 'update-kubeconfig', '--region', region, '--name', cluster_name]
        process_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if process_result.returncode == 0:
            result['status'] = 'success'
            # Verify kubectl can connect to the cluster
            verify_result = subprocess.run(['kubectl', 'cluster-info'], capture_output=True, text=True, timeout=10)
            if verify_result.returncode != 0:
                result['status'] = 'verification_failed'
                result['error'] = 'kubectl configuration succeeded but cluster connection failed'
        else:
            result['status'] = 'failed'
            result['error'] = process_result.stderr or 'Failed to configure kubectl'
            
    except subprocess.TimeoutExpired:
        result['status'] = 'timeout'
        result['error'] = 'kubectl configuration timed out'
    except FileNotFoundError:
        result['status'] = 'aws_cli_not_found'
        result['error'] = 'AWS CLI not found in PATH'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def run_kubent_scan(cluster_name: str) -> Dict[str, Any]:
    """Run kubent scan for deprecated APIs."""
    results = {
        'status': 'not_run',
        'deprecated_apis': [],
        'error': None
    }
    
    try:
        # Check if kubent is available
        result = subprocess.run(['kubent', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            results['status'] = 'tool_not_found'
            results['error'] = 'kubent not found in PATH'
            return results
        
        # Check if kubectl is configured for the cluster
        kubectl_check = subprocess.run(['kubectl', 'cluster-info'], capture_output=True, text=True, timeout=10)
        if kubectl_check.returncode != 0:
            results['status'] = 'kubectl_not_configured'
            results['error'] = f'kubectl not configured for cluster {cluster_name}. Configure kubectl first.'
            return results
        
        # Run kubent scan with shorter timeout for multi-cluster scenarios
        # Disable helm3 and cluster collectors to speed up scanning
        cmd = ['kubent', '--output', 'json', '--target-version', '1.33', '--cluster=false', '--helm3=false']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            if result.stdout.strip():
                try:
                    # Parse JSON output with comprehensive error handling
                    kubent_output = json.loads(result.stdout)
                    results['status'] = 'success'
                    
                    # Safely extract deprecated APIs with multiple fallbacks
                    deprecated_apis = []
                    
                    if kubent_output is None:
                        deprecated_apis = []
                    elif isinstance(kubent_output, dict):
                        # Try different possible keys
                        deprecated_apis = (kubent_output.get('items') or 
                                         kubent_output.get('results') or 
                                         kubent_output.get('deprecated') or [])
                    elif isinstance(kubent_output, list):
                        deprecated_apis = kubent_output
                    else:
                        # Single item or unknown format
                        deprecated_apis = [kubent_output] if kubent_output else []
                    
                    # Ensure we have a list
                    if not isinstance(deprecated_apis, list):
                        deprecated_apis = [deprecated_apis]
                    
                    results['deprecated_apis'] = deprecated_apis
                    
                except json.JSONDecodeError as e:
                    results['status'] = 'parse_error'
                    results['error'] = f'Failed to parse kubent JSON: {str(e)}'
                    results['raw_output'] = result.stdout[:500]
                except Exception as e:
                    results['status'] = 'parse_error'
                    results['error'] = f'Error processing kubent output: {str(e)}'
                    results['raw_output'] = result.stdout[:500]
            else:
                # Empty output means no deprecated APIs found
                results['status'] = 'success'
                results['deprecated_apis'] = []
        else:
            results['status'] = 'scan_failed'
            results['error'] = result.stderr or 'kubent scan failed'
            
    except subprocess.TimeoutExpired:
        results['status'] = 'timeout'
        results['error'] = 'kubent scan timed out after 10 seconds'
    except FileNotFoundError:
        results['status'] = 'tool_not_found'
        results['error'] = 'kubent not found in PATH'
    except Exception as e:
        results['status'] = 'error'
        results['error'] = f'kubent scan exception: {str(e)}'
        # Add debug information for troubleshooting
        import traceback
        results['debug_trace'] = traceback.format_exc()
    
    return results


def run_kubent_scan_fast(cluster_name: str, timeout: int = 5) -> Dict[str, Any]:
    """Run kubent scan with optimized settings for large cluster counts."""
    results = {
        'status': 'not_run',
        'deprecated_apis': [],
        'error': None
    }
    
    try:
        # Check if kubent is available (quick check)
        result = subprocess.run(['kubent', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            results['status'] = 'tool_not_found'
            results['error'] = 'kubent not found in PATH'
            return results
        
        # Skip kubectl check for speed in large cluster scenarios
        # Assume kubectl is configured if we got this far
        
        # Run kubent scan with very aggressive optimizations for speed
        cmd = [
            'kubent', 
            '--output', 'json', 
            '--target-version', '1.33',
            '--cluster=false',  # Disable cluster-wide scanning
            '--helm3=false',    # Disable Helm scanning
            '--log-level', 'error'  # Reduce logging overhead
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0:
            if result.stdout.strip():
                try:
                    # Parse JSON output with comprehensive error handling
                    kubent_output = json.loads(result.stdout)
                    results['status'] = 'success'
                    
                    # Safely extract deprecated APIs with multiple fallbacks
                    deprecated_apis = []
                    
                    if kubent_output is None:
                        deprecated_apis = []
                    elif isinstance(kubent_output, dict):
                        # Try different possible keys
                        deprecated_apis = (kubent_output.get('items') or 
                                         kubent_output.get('results') or 
                                         kubent_output.get('deprecated') or [])
                    elif isinstance(kubent_output, list):
                        deprecated_apis = kubent_output
                    else:
                        # Single item or unknown format
                        deprecated_apis = [kubent_output] if kubent_output else []
                    
                    # Ensure we have a list
                    if not isinstance(deprecated_apis, list):
                        deprecated_apis = [deprecated_apis]
                    
                    results['deprecated_apis'] = deprecated_apis
                    
                except json.JSONDecodeError as e:
                    results['status'] = 'parse_error'
                    results['error'] = f'Failed to parse kubent JSON: {str(e)}'
                    results['raw_output'] = result.stdout[:200]  # Shorter for fast mode
                except Exception as e:
                    results['status'] = 'parse_error'
                    results['error'] = f'Error processing kubent output: {str(e)}'
                    results['raw_output'] = result.stdout[:200]
            else:
                # Empty output means no deprecated APIs found
                results['status'] = 'success'
                results['deprecated_apis'] = []
        else:
            results['status'] = 'scan_failed'
            results['error'] = result.stderr or 'kubent scan failed'
            
    except subprocess.TimeoutExpired:
        results['status'] = 'timeout'
        results['error'] = f'kubent scan timed out after {timeout} seconds (fast mode)'
    except FileNotFoundError:
        results['status'] = 'tool_not_found'
        results['error'] = 'kubent not found in PATH'
    except Exception as e:
        results['status'] = 'error'
        results['error'] = f'kubent scan exception: {str(e)}'
    
    return results


def run_pluto_scan(cluster_name: str) -> Dict[str, Any]:
    """Run pluto scan for deprecated APIs."""
    results = {
        'status': 'not_run',
        'deprecated_apis': [],
        'error': None
    }
    
    try:
        # Check if pluto is available
        result = subprocess.run(['pluto', 'version'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            results['status'] = 'tool_not_found'
            results['error'] = 'pluto not found in PATH'
            return results
        
        # Check if kubectl is configured for the cluster
        kubectl_check = subprocess.run(['kubectl', 'cluster-info'], capture_output=True, text=True, timeout=10)
        if kubectl_check.returncode != 0:
            results['status'] = 'kubectl_not_configured'
            results['error'] = f'kubectl not configured for cluster {cluster_name}. Configure kubectl first.'
            return results
        
        # Run pluto scan
        cmd = ['pluto', 'detect-all-in-cluster', '--output', 'json']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            try:
                if result.stdout.strip():
                    pluto_output = json.loads(result.stdout)
                    results['status'] = 'success'
                    
                    # Handle different pluto JSON output formats
                    if isinstance(pluto_output, dict):
                        # Standard format: {"items": [...]}
                        results['deprecated_apis'] = pluto_output.get('items', [])
                    elif isinstance(pluto_output, list):
                        # Direct list format: [...]
                        results['deprecated_apis'] = pluto_output
                    else:
                        # Unknown format, store as single item
                        results['deprecated_apis'] = [pluto_output]
                else:
                    # Empty output means no deprecated APIs found
                    results['status'] = 'success'
                    results['deprecated_apis'] = []
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to parse text output or return error
                results['status'] = 'parse_error'
                results['error'] = f'Failed to parse pluto JSON output: {str(e)}'
                results['raw_output'] = result.stdout
        else:
            results['status'] = 'scan_failed'
            results['error'] = result.stderr or 'pluto scan failed'
            
    except subprocess.TimeoutExpired:
        results['status'] = 'timeout'
        results['error'] = 'pluto scan timed out'
    except FileNotFoundError:
        results['status'] = 'tool_not_found'
        results['error'] = 'pluto not found in PATH'
    except Exception as e:
        results['status'] = 'error'
        results['error'] = str(e)
    
    return results


def check_deprecated_apis(aws_client: AWSClient, cluster_name: str) -> Dict[str, Any]:
    """Check for deprecated API usage via metrics and audit logs."""
    results = {
        'status': 'not_run',
        'metrics_check': {'status': 'not_run', 'deprecated_apis': []},
        'audit_logs_check': {'status': 'not_run', 'deprecated_apis': []},
        'error': None
    }
    
    try:
        # Check kubectl availability for metrics
        try:
            result = subprocess.run(['kubectl', 'version', '--client'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Try to get deprecated API metrics
                metrics_result = subprocess.run(
                    ['kubectl', 'get', '--raw', '/metrics'], 
                    capture_output=True, text=True, timeout=30
                )
                if metrics_result.returncode == 0:
                    # Parse metrics for deprecated APIs
                    deprecated_metrics = []
                    for line in metrics_result.stdout.split('\n'):
                        if 'apiserver_requested_deprecated_apis' in line and not line.startswith('#'):
                            deprecated_metrics.append(line.strip())
                    
                    results['metrics_check'] = {
                        'status': 'success',
                        'deprecated_apis': deprecated_metrics
                    }
                else:
                    results['metrics_check'] = {
                        'status': 'failed',
                        'error': 'Failed to get metrics from cluster'
                    }
            else:
                results['metrics_check'] = {
                    'status': 'kubectl_not_configured',
                    'error': 'kubectl not configured for cluster access'
                }
        except Exception as e:
            results['metrics_check'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Check audit logs via CloudWatch Logs
        try:
            import time
            from datetime import datetime, timedelta
            
            # Start CloudWatch Logs query
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)  # Last hour
            
            query_response = aws_client.logs_client.start_query(
                logGroupName=f'/aws/eks/{cluster_name}/cluster',
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString='fields @message | filter `annotations.k8s.io/deprecated`="true"'
            )
            
            query_id = query_response['queryId']
            
            # Wait for query to complete
            time.sleep(5)
            
            query_results = aws_client.logs_client.get_query_results(queryId=query_id)
            
            if query_results['status'] == 'Complete':
                results['audit_logs_check'] = {
                    'status': 'success',
                    'deprecated_apis': query_results.get('results', [])
                }
            else:
                results['audit_logs_check'] = {
                    'status': 'query_incomplete',
                    'error': f"Query status: {query_results['status']}"
                }
                
        except Exception as e:
            results['audit_logs_check'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Set overall status
        if (results['metrics_check']['status'] == 'success' or 
            results['audit_logs_check']['status'] == 'success'):
            results['status'] = 'success'
        else:
            results['status'] = 'partial_failure'
            
    except Exception as e:
        results['status'] = 'error'
        results['error'] = str(e)
    
    return results


def generate_web_ui_dashboard(cluster_analysis: dict, output_dir: str):
    """Generate web UI dashboard with assessment data."""
    try:
        import shutil
        
        # Extract cluster metadata for web UI
        clusters_metadata = {}
        for cluster_name, analysis in cluster_analysis.items():
            clusters_metadata[cluster_name] = analysis.get('cluster_metadata', {})
        
        # Create web UI directory structure
        web_ui_dir = Path(output_dir) / "web-ui"
        web_ui_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy web UI files from the toolkit's web-ui directory
        toolkit_web_ui = Path("web-ui")
        if toolkit_web_ui.exists():
            # Copy package.json
            if (toolkit_web_ui / "package.json").exists():
                shutil.copy2(toolkit_web_ui / "package.json", web_ui_dir / "package.json")
            
            # Copy public directory
            if (toolkit_web_ui / "public").exists():
                if (web_ui_dir / "public").exists():
                    shutil.rmtree(web_ui_dir / "public")
                shutil.copytree(toolkit_web_ui / "public", web_ui_dir / "public")
            
            # Copy src directory
            if (toolkit_web_ui / "src").exists():
                if (web_ui_dir / "src").exists():
                    shutil.rmtree(web_ui_dir / "src")
                shutil.copytree(toolkit_web_ui / "src", web_ui_dir / "src")
        
        # Create assessment data file for web UI
        assessment_data_file = web_ui_dir / "public" / "assessment-data.json"
        assessment_data_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(assessment_data_file, 'w') as f:
            json.dump(clusters_metadata, f, indent=2, default=str)
        
        print(f"✅ Web UI generated at: {web_ui_dir}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate web UI: {str(e)}")


def generate_assessment_readme(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate main assessment README file."""
    readme_content = f"""# EKS Upgrade Assessment Report

## Overview
This assessment provides comprehensive analysis of your EKS clusters for upgrade readiness following AWS best practices.

**Target Region:** {config.aws_configuration.region}
**Assessment Date:** Generated on analysis run
**Clusters Assessed:** {len(cluster_analysis)}

## Assessment Summary
"""
    
    for cluster_name, analysis in cluster_analysis.items():
        cluster_info = analysis['cluster_info']
        insights = analysis.get('insights', [])
        kubent_results = analysis.get('kubent_results', {})
        pluto_results = analysis.get('pluto_results', {})
        
        # Determine overall assessment result
        has_critical_issues = (
            any(insight.get('insightStatus', {}).get('status') == 'ERROR' for insight in insights) or
            (kubent_results.get('status') == 'success' and len(kubent_results.get('deprecated_apis', [])) > 0) or
            (pluto_results.get('status') == 'success' and len(pluto_results.get('deprecated_apis', [])) > 0)
        )
        
        if has_critical_issues:
            assessment_result = "❌ NEEDS ATTENTION"
        else:
            assessment_result = "✅ READY FOR UPGRADE"
        
        readme_content += f"""
### {cluster_name}
- **Current Version:** {cluster_info.version}
- **Target Version:** {config.upgrade_targets.control_plane_target_version}
- **Status:** {cluster_info.status}
- **Assessment Result:** {assessment_result}
- **Node Groups:** {len(analysis['node_groups'])}
- **Fargate Profiles:** {len(analysis['fargate_profiles'])}
- **Addons:** {len(analysis['addons'])}
"""
    
    readme_content += """
## Assessment Structure

1. **[Assessment Reports](assessment-reports/)** - Detailed cluster readiness analysis
2. **[Cluster Metadata](cluster-metadata/)** - Complete cluster configuration data
3. **[Scripts](scripts/)** - Assessment validation and helper scripts

## Key Findings

### Deprecated APIs
Review the assessment reports for any deprecated APIs that need attention before upgrade.

### Cluster Insights
EKS Cluster Insights findings are included in the detailed assessment reports.

### Resource Inventory
Complete AWS resource inventory is available for each cluster to understand dependencies.

## Next Steps

1. Review the detailed assessment reports in the `assessment-reports/` folder
2. Address any critical issues identified in the assessment
3. Plan your upgrade strategy based on the findings
4. Use the cluster metadata for upgrade planning and rollback preparation

## Important Notes

⚠️ **Assessment Scope**: This assessment focuses on upgrade readiness analysis only.

⚠️ **Deprecated APIs**: Pay special attention to any deprecated APIs that will be removed in the target Kubernetes version.

## Support

For detailed upgrade guidance, refer to the AWS EKS documentation and best practices guide.
"""
    
    with open(Path(output_dir, "README.md"), 'w') as f:
        f.write(readme_content)


def generate_cluster_metadata_json(cluster_analysis: dict, output_dir: str):
    """Generate comprehensive cluster metadata JSON file (without addon compatibility)."""
    try:
        # Extract cluster metadata only (exclude addon compatibility)
        clusters_metadata = {}
        for cluster_name, analysis in cluster_analysis.items():
            cluster_metadata = analysis.get('cluster_metadata', {})
            # Explicitly exclude addon_compatibility from cluster metadata
            clusters_metadata[cluster_name] = cluster_metadata
        
        # Save to assessment-reports directory
        metadata_file = Path(output_dir) / "assessment-reports" / "clusters-metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_file, 'w') as f:
            json.dump(clusters_metadata, f, indent=2, default=str)
        
        print(f"✅ Cluster metadata JSON saved to: {metadata_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate cluster metadata JSON: {str(e)}")


def generate_assessment_scripts(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate assessment validation scripts."""
    try:
        scripts_dir = Path(output_dir) / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate cluster validation script
        validation_script = f"""#!/bin/bash
# EKS Cluster Assessment Validation Script
# Generated for region: {config.aws_configuration.region}

set -e

REGION="{config.aws_configuration.region}"
CLUSTERS=({' '.join([f'"{name}"' for name in cluster_analysis.keys()])})

echo "✅ Running EKS cluster assessment validation..."

for CLUSTER in "${{CLUSTERS[@]}}"; do
    echo "Validating cluster: $CLUSTER"
    
    # Check cluster status
    echo "  🔍 Checking cluster status..."
    STATUS=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.status' --output text)
    VERSION=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.version' --output text)
    echo "    Cluster status: $STATUS"
    echo "    Cluster version: $VERSION"
    
    if [ "$STATUS" != "ACTIVE" ]; then
        echo "    ❌ Cluster is not in ACTIVE state!"
        continue
    fi
    
    # Check node groups
    echo "  🖥️  Checking node groups..."
    aws eks list-nodegroups --region $REGION --cluster-name $CLUSTER --query 'nodegroups' --output table
    
    # Check Fargate profiles
    echo "  🚀 Checking Fargate profiles..."
    aws eks list-fargate-profiles --region $REGION --cluster-name $CLUSTER --query 'fargateProfileNames' --output table
    
    # Check EKS add-ons
    echo "  🔧 Checking EKS add-ons..."
    aws eks list-addons --region $REGION --cluster-name $CLUSTER --output table
    
    echo "  ✅ Validation complete for $CLUSTER"
    echo ""
done

echo "✅ Assessment validation completed"
"""
        
        validation_script_file = scripts_dir / "assessment-validation.sh"
        with open(validation_script_file, 'w') as f:
            f.write(validation_script)
        
        # Make script executable
        validation_script_file.chmod(0o755)
        
        print(f"✅ Assessment validation script generated: {validation_script_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate assessment scripts: {str(e)}")


def generate_web_ui_from_reports(cluster_analysis: dict, output_dir: str):
    """Generate web UI inside assessment-reports using the generated report data."""
    try:
        from jinja2 import Environment, FileSystemLoader
        
        # Create web UI directory (output_dir now includes full path)
        web_ui_dir = Path(output_dir) / "web-ui"
        web_ui_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Create assessment data for the web UI (simplified format)
        assessment_data = {}
        for cluster_name, analysis in cluster_analysis.items():
            cluster_info = analysis.get('cluster_info', {})
            insights = analysis.get('insights', [])
            kubent_results = analysis.get('kubent_results', {})
            pluto_results = analysis.get('pluto_results', {})
            cluster_metadata = analysis.get('cluster_metadata', {})
            
            # Create simplified assessment data for web UI (no cluster metadata duplication)
            assessment_data[cluster_name] = {
                'cluster_info': {
                    'name': cluster_name,
                    'version': cluster_info.version if hasattr(cluster_info, 'version') else cluster_metadata.get('cluster_version', 'Unknown'),
                    'status': cluster_info.status if hasattr(cluster_info, 'status') else cluster_metadata.get('cluster_status', 'Unknown'),
                    'endpoint': cluster_info.endpoint if hasattr(cluster_info, 'endpoint') else 'Unknown'
                },
                'assessment_results': {
                    'insights': {
                        'status': determine_insights_status(insights),
                        'count': len(insights),
                        'critical_issues': len([i for i in insights if i.get('insightStatus', {}).get('status') == 'ERROR']),
                        'warning_issues': len([i for i in insights if i.get('insightStatus', {}).get('status') == 'WARNING']),
                        'findings': insights[:5]  # Limit for web UI
                    },
                    'deprecated_apis': {
                        'kubent': {
                            'status': kubent_results.get('status', 'not_run'),
                            'count': len(kubent_results.get('deprecated_apis', [])),
                            'apis': kubent_results.get('deprecated_apis', [])[:10]  # Limit for web UI
                        },
                        'pluto': {
                            'status': pluto_results.get('status', 'not_run'),
                            'count': len(pluto_results.get('deprecated_apis', [])),
                            'apis': pluto_results.get('deprecated_apis', [])[:10]  # Limit for web UI
                        }
                    },
                    'addon_compatibility': analysis.get('addon_compatibility', {}),
                    'addon_iam_analysis': analysis.get('addon_iam_analysis', {})
                },
                'cluster_metadata': cluster_metadata
            }
        # Step 2: Save assessment data JSON for web UI
        assessment_data_file = web_ui_dir / "assessment-data.json"
        with open(assessment_data_file, 'w') as f:
            json.dump(assessment_data, f, indent=2, default=str)
        
        # Step 2.1: Copy clusters-metadata.json to web-ui directory for direct access
        clusters_metadata_source = Path(output_dir) / "clusters-metadata.json"  # output_dir now includes full path
        clusters_metadata_dest = web_ui_dir / "clusters-metadata.json"
        if clusters_metadata_source.exists():
            import shutil
            shutil.copy2(clusters_metadata_source, clusters_metadata_dest)
        else:
            # Create clusters metadata from cluster_analysis if source doesn't exist
            clusters_metadata = {}
            for cluster_name, analysis in cluster_analysis.items():
                clusters_metadata[cluster_name] = analysis.get('cluster_metadata', {})
            
            with open(clusters_metadata_dest, 'w') as f:
                json.dump(clusters_metadata, f, indent=2, default=str)
        
        # Step 3: Generate HTML dashboard using template
        try:
            # Try to use the template system
            from datetime import datetime
            template_dir = Path(__file__).parent.parent / "templates"
            if template_dir.exists():
                env = Environment(loader=FileSystemLoader(str(template_dir)))
                template = env.get_template('web-dashboard.html.j2')
                
                # Prepare clusters metadata from cluster_analysis
                clusters_metadata = {}
                for cluster_name, analysis in cluster_analysis.items():
                    clusters_metadata[cluster_name] = analysis.get('cluster_metadata', {})
                
                # Custom JSON serializer for datetime objects
                def json_serial(obj):
                    """JSON serializer for objects not serializable by default json code"""
                    if hasattr(obj, 'isoformat'):
                        return obj.isoformat()
                    return str(obj)
                
                # Convert data to JSON-serializable format before passing to template
                clusters_metadata_json = json.loads(json.dumps(clusters_metadata, default=json_serial))
                assessment_data_json = json.loads(json.dumps(assessment_data, default=json_serial))
                
                html_content = template.render(
                    clusters_metadata=clusters_metadata_json,
                    assessment_data=assessment_data_json,
                    generation_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                )
            else:
                # Fallback to inline HTML generation
                html_content = generate_assessment_dashboard_html_inline(assessment_data, cluster_analysis)
        except Exception as template_error:
            print(f"⚠️  Template error: {template_error}, using fallback HTML generation")
            html_content = generate_assessment_dashboard_html_inline(assessment_data, cluster_analysis)
        
        # Step 4: Save HTML dashboard
        html_file = web_ui_dir / "index.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"✅ Web UI dashboard generated: {html_file}")
        print(f"✅ Assessment data saved: {assessment_data_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate web UI from reports: {str(e)}")


def generate_assessment_dashboard_html_inline(assessment_data: dict, cluster_analysis: dict) -> str:
    """Generate HTML content for the assessment dashboard using inline template."""
    from datetime import datetime
    
    # Prepare clusters metadata from cluster_analysis
    clusters_metadata = {}
    for cluster_name, analysis in cluster_analysis.items():
        clusters_metadata[cluster_name] = analysis.get('cluster_metadata', {})
    
    # Read the template file directly
    template_path = Path(__file__).parent.parent / "templates" / "web-dashboard.html.j2"
    
    if template_path.exists():
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Simple template variable replacement (basic implementation)
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        html_content = template_content.replace(
            '{{ clusters_metadata | tojson }}', 
            json.dumps(clusters_metadata, default=json_serial, indent=2)
        ).replace(
            '{{ assessment_data | tojson }}', 
            json.dumps(assessment_data, default=json_serial, indent=2)
        ).replace(
            '{{ generation_time }}', 
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        return html_content
    else:
        # Ultimate fallback - basic HTML
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EKS Upgrade Assessment Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #232f3e; color: white; padding: 20px; text-align: center; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .cluster-info {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 EKS Upgrade Assessment Dashboard</h1>
        <p>Interactive analysis of your EKS clusters for upgrade readiness</p>
    </div>
    <div class="container">
        <h2>Clusters Overview</h2>
        {''.join([f'<div class="cluster-info"><h3>{name}</h3><p>Status: {data.get("cluster_metadata", {}).get("cluster_status", "Unknown")}</p></div>' for name, data in assessment_data.items()])}
        <script>
            console.log('Dashboard loaded with {len(assessment_data)} clusters');
            const clustersData = {json.dumps(clusters_metadata, default=str)};
            const assessmentData = {json.dumps(assessment_data, default=str)};
        </script>
    </div>
</body>
</html>
        """


def generate_assessment_dashboard_html(assessment_data: dict) -> str:
    """Generate HTML content for the assessment dashboard."""
    
    # Calculate summary statistics
    total_clusters = len(assessment_data)
    clusters_with_issues = 0
    total_deprecated_apis = 0
    total_critical_insights = 0
    
    for cluster_name, data in assessment_data.items():
        insights = data.get('assessment_results', {}).get('insights', {})
        kubent = data.get('assessment_results', {}).get('deprecated_apis', {}).get('kubent', {})
        pluto = data.get('assessment_results', {}).get('deprecated_apis', {}).get('pluto', {})
        
        critical_issues = insights.get('critical_issues', 0)
        deprecated_count = kubent.get('count', 0) + pluto.get('count', 0)
        
        if critical_issues > 0 or deprecated_count > 0:
            clusters_with_issues += 1
        
        total_deprecated_apis += deprecated_count
        total_critical_insights += critical_issues
    
    # Generate cluster sections HTML
    cluster_sections = ""
    for cluster_name, data in assessment_data.items():
        cluster_info = data.get('cluster_info', {})
        assessment_results = data.get('assessment_results', {})
        metadata = data.get('cluster_metadata', {})
        
        insights = assessment_results.get('insights', {})
        kubent = assessment_results.get('deprecated_apis', {}).get('kubent', {})
        pluto = assessment_results.get('deprecated_apis', {}).get('pluto', {})
        
        # Determine overall status
        critical_issues = insights.get('critical_issues', 0)
        deprecated_count = kubent.get('count', 0) + pluto.get('count', 0)
        
        if critical_issues > 0 or deprecated_count > 0:
            status_text = "❌ NEEDS ATTENTION"
        else:
            status_text = "✅ READY"
        
        cluster_sections += f"""
        <div class="cluster-section">
            <h2 class="cluster-title">{cluster_name} - {status_text}</h2>
            
            <div class="status-grid">
                <div class="status-item">
                    <div class="status-value">{cluster_info.get('version', 'Unknown')}</div>
                    <div class="status-label">Kubernetes Version</div>
                </div>
                <div class="status-item">
                    <div class="status-value">{cluster_info.get('status', 'Unknown')}</div>
                    <div class="status-label">Cluster Status</div>
                </div>
                <div class="status-item {'warning' if critical_issues > 0 else ''}">
                    <div class="status-value">{critical_issues}</div>
                    <div class="status-label">Critical Insights</div>
                </div>
                <div class="status-item {'warning' if deprecated_count > 0 else ''}">
                    <div class="status-value">{deprecated_count}</div>
                    <div class="status-label">Deprecated APIs</div>
                </div>
                <div class="status-item">
                    <div class="status-value">{metadata.get('node_groups', 0)}</div>
                    <div class="status-label">Node Groups</div>
                </div>
                <div class="status-item">
                    <div class="status-value">{metadata.get('addons', 0)}</div>
                    <div class="status-label">EKS Add-ons</div>
                </div>
            </div>
        </div>
        """
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EKS Upgrade Assessment Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #0073bb;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 25px;
            border-radius: 8px;
            border-left: 4px solid #0073bb;
            text-align: center;
        }}
        .summary-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #0073bb;
            margin-bottom: 10px;
        }}
        .summary-label {{
            color: #666;
            font-size: 1.1em;
        }}
        .cluster-section {{
            margin: 40px 0;
            padding: 25px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
        }}
        .cluster-title {{
            color: #232f3e;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #ddd;
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .status-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 3px solid #28a745;
        }}
        .status-item.warning {{
            border-left-color: #ffc107;
        }}
        .status-value {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .status-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 EKS Upgrade Assessment Dashboard</h1>
            <p>Comprehensive analysis of your EKS clusters for upgrade readiness</p>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-value">{total_clusters}</div>
                <div class="summary-label">Total Clusters</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{clusters_with_issues}</div>
                <div class="summary-label">Clusters Need Attention</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{total_critical_insights}</div>
                <div class="summary-label">Critical Insights</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{total_deprecated_apis}</div>
                <div class="summary-label">Deprecated APIs Found</div>
            </div>
        </div>
        
        {cluster_sections}
        
        <div class="footer">
            <p>Generated by EKS Upgrade Assessment Toolkit | AWS Best Practices</p>
            <p>Review the detailed assessment reports and cluster metadata for complete analysis</p>
        </div>
    </div>
</body>
</html>
    """
    
    return html_content


def get_status_emoji(status: str) -> str:
    """Convert status to emoji representation."""
    status_map = {
        'success': '✅ PASS',
        'failed': '❌ FAIL',
        'error': '❌ ERROR',
        'timeout': '⏰ TIMEOUT',
        'tool_not_found': '🔧 MISSING',
        'kubectl_not_configured': '⚙️ CONFIG',
        'not_run': '⏸️ SKIPPED',
        'skipped': '⏸️ SKIPPED',
        'parse_error': '📄 PARSE_ERROR'
    }
    return status_map.get(status, f'❓ {status.upper()}')

def generate_assessment_reports(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate assessment reports."""
    assessment_dir = Path(output_dir)  # output_dir now includes the full path
    
    # Generate assessment report with table format
    report_content = "# Pre-upgrade Assessment Report\n\n"
    
    # Generate summary table
    report_content += "## Assessment Summary\n\n"
    report_content += "| Cluster Name | Overall Result | Current Version | Target Version | Status | Insights Status | Kubent Status | Pluto Status | Deprecated APIs |\n"
    report_content += "|--------------|----------------|----------------|----------------|--------|----------------|---------------|--------------|-----------------|\n"
    
    for cluster_name, analysis in cluster_analysis.items():
        cluster_info = analysis['cluster_info']
        insights = analysis.get('insights', [])
        kubent_results = analysis.get('kubent_results', {})
        pluto_results = analysis.get('pluto_results', {})
        deprecated_api_results = analysis.get('deprecated_api_results', {})
        
        # Determine overall status with proper WARNING and ERROR handling
        if any(insight.get('insightStatus', {}).get('status') == 'ERROR' for insight in insights):
            insights_status = "❌ ISSUES"
        elif any(insight.get('insightStatus', {}).get('status') == 'WARNING' for insight in insights):
            insights_status = "⚠️ WARNING"
        else:
            insights_status = "✅ PASS"
        
        # Check if kubent found deprecated APIs (not just if the scan succeeded)
        if kubent_results.get('status') == 'success' and len(kubent_results.get('deprecated_apis', [])) > 0:
            kubent_status = "❌ FOUND"
        else:
            kubent_status = get_status_emoji(kubent_results.get('status', 'not_run'))
        
        # Check if pluto found deprecated APIs (not just if the scan succeeded)
        if pluto_results.get('status') == 'success' and len(pluto_results.get('deprecated_apis', [])) > 0:
            pluto_status = "❌ FOUND"
        else:
            pluto_status = get_status_emoji(pluto_results.get('status', 'not_run'))
        
        # Check if deprecated APIs were actually found (not just if the check succeeded)
        deprecated_apis_found = False
        if deprecated_api_results.get('status') == 'success':
            metrics_apis = deprecated_api_results.get('metrics_check', {}).get('deprecated_apis', [])
            audit_apis = deprecated_api_results.get('audit_logs_check', {}).get('deprecated_apis', [])
            deprecated_apis_found = len(metrics_apis) > 0 or len(audit_apis) > 0
        
        if deprecated_apis_found:
            deprecated_api_status = "❌ FOUND"
        else:
            deprecated_api_status = get_status_emoji(deprecated_api_results.get('status', 'not_run'))
        
        # Calculate overall result with improved logic
        # Check for critical issues that require immediate attention
        has_critical_issues = (
            any(insight.get('insightStatus', {}).get('status') == 'ERROR' for insight in insights) or
            (kubent_results.get('status') == 'success' and len(kubent_results.get('deprecated_apis', [])) > 0) or
            (pluto_results.get('status') == 'success' and len(pluto_results.get('deprecated_apis', [])) > 0)
        )
        
        # Check for deprecated API usage that might not be critical (if EKS Insights pass)
        has_deprecated_api_usage = (
            deprecated_api_results.get('status') == 'success' and 
            (len(deprecated_api_results.get('metrics_check', {}).get('deprecated_apis', [])) > 0 or
             len(deprecated_api_results.get('audit_logs_check', {}).get('deprecated_apis', [])) > 0)
        )
        
        # Check if EKS Insights show any deprecated API issues for target versions
        eks_insights_has_deprecated_issues = any(
            insight.get('insightStatus', {}).get('status') == 'ERROR' and 
            'deprecated' in insight.get('name', '').lower()
            for insight in insights
        )
        
        # Determine overall result based on severity
        if has_critical_issues:
            overall_result = "❌ NEEDS ATTENTION"
        elif has_deprecated_api_usage and eks_insights_has_deprecated_issues:
            overall_result = "❌ NEEDS ATTENTION"  # EKS Insights confirm this is critical
        elif has_deprecated_api_usage:
            overall_result = "⚠️ WARNING"  # Deprecated APIs found but EKS Insights show PASSING
        else:
            overall_result = "✅ READY"
        
        report_content += f"| {cluster_name} | {overall_result} | {cluster_info.version} | {config.upgrade_targets.control_plane_target_version} | {cluster_info.status} | {insights_status} | {kubent_status} | {pluto_status} | {deprecated_api_status} |\n"
    
    # Save the report
    with open(assessment_dir / "assessment-report.md", 'w') as f:
        f.write(report_content)

def generate_documentation(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate assessment documentation based on analysis."""
    # Create directory structure for assessment only
    dirs_to_create = [
        "assessment-reports",
        "cluster-metadata", 
        "scripts"
    ]
    
    for dir_name in dirs_to_create:
        Path(output_dir, dir_name).mkdir(parents=True, exist_ok=True)
    
    # Step 1: Generate main README
    generate_assessment_readme(config, cluster_analysis, output_dir)
    
    # Step 2: Generate assessment reports and data first
    generate_assessment_reports(config, cluster_analysis, output_dir)
    
    # Step 3: Generate cluster metadata JSON
    # Step 2.5: Generate separate addon compatibility report
    click.echo("📝 Generating addon compatibility report...")
    addon_compatibility_report = {}
    
    for cluster_name, analysis in cluster_analysis.items():
        addon_compatibility = analysis.get('addon_compatibility', {})
        if addon_compatibility:
            addon_compatibility_report[cluster_name] = addon_compatibility
    
    # Save addon compatibility to separate file
    if addon_compatibility_report:
        addon_compatibility_file = Path(output_dir) / "assessment-reports" / "addon-compatibility.json"
        addon_compatibility_file.parent.mkdir(parents=True, exist_ok=True)
        with open(addon_compatibility_file, 'w') as f:
            json.dump(addon_compatibility_report, f, indent=2, default=str)
        click.echo(f"✅ Addon compatibility report saved to: {addon_compatibility_file}")
    
    # Step 2.6: Generate separate addon IAM analysis report
    click.echo("📝 Generating addon IAM analysis report...")
    addon_iam_report = {}
    
    for cluster_name, analysis in cluster_analysis.items():
        addon_iam_analysis = analysis.get('addon_iam_analysis', {})
        if addon_iam_analysis:
            addon_iam_report[cluster_name] = addon_iam_analysis
    
    # Save addon IAM analysis to separate file
    if addon_iam_report:
        addon_iam_file = Path(output_dir) / "assessment-reports" / "addon-iam-analysis.json"
        addon_iam_file.parent.mkdir(parents=True, exist_ok=True)
        with open(addon_iam_file, 'w') as f:
            json.dump(addon_iam_report, f, indent=2, default=str)
        click.echo(f"✅ Addon IAM analysis report saved to: {addon_iam_file}")
    
    generate_cluster_metadata_json(cluster_analysis, output_dir)
    
    # Step 4: Generate assessment scripts
    generate_assessment_scripts(config, cluster_analysis, output_dir)
    
    # Step 5: Generate web UI using the generated report data (last step)
    generate_web_ui_from_reports(cluster_analysis, output_dir)


if __name__ == '__main__':
    
    try:
        cli()
        app_content = f.read()
        
        # Replace mock data loading with actual file loading
        updated_content = app_content.replace(
            "// In a real implementation, this would fetch from the actual file\n      // For now, we'll use mock data based on the structure we created",
            "// Load actual assessment data from the generated file"
        ).replace(
            "const mockData = {",
            "const response = await fetch('/assessment-data.json');\n      const actualData = await response.json();\n      const mockData = actualData || {"
        )
        
        with open(app_js_file, 'w') as f:
            f.write(updated_content)
        
        # Generate standalone HTML report
        generate_html_report(clusters_metadata, output_dir)
        
        print(f"✅ Web UI generated at: {web_ui_dir}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate web UI: {str(e)}")

def generate_html_report(clusters_data: dict, output_dir: str):
    """Generate a standalone HTML report."""
    try:
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EKS Upgrade Assessment Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            color: #232f3e;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #0073bb;
        }}
        .summary-value {{
            font-size: 2em;
            font-weight: bold;
            color: #0073bb;
        }}
        .summary-label {{
            color: #666;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
            vertical-align: top;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .status-active {{ color: #28a745; }}
        .status-degraded {{ color: #ffc107; }}
        .status-failed {{ color: #dc3545; }}
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.875em;
            font-weight: 500;
            margin: 2px;
            display: inline-block;
        }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-info {{ background: #d1ecf1; color: #0c5460; }}
        .badge-primary {{ background: #cce5ff; color: #004085; }}
        .cluster-row {{
            cursor: pointer;
            transition: background-color 0.2s;
        }}
        .cluster-row:hover {{
            background-color: #f8f9fa;
        }}
        .cluster-details {{
            display: none;
            background-color: #f8f9fa;
            border-left: 4px solid #0073bb;
        }}
        .cluster-details.show {{
            display: table-row;
        }}
        .details-content {{
            padding: 20px;
        }}
        .details-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .details-section {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #e1e4e8;
        }}
        .details-section h4 {{
            margin-top: 0;
            color: #0073bb;
            border-bottom: 1px solid #e1e4e8;
            padding-bottom: 8px;
        }}
        .resource-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .resource-item {{
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .resource-item:last-child {{
            border-bottom: none;
        }}
        .expand-icon {{
            font-size: 0.8em;
            color: #666;
            margin-left: 8px;
        }}
        .plugins-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }}
    </style>
    <script>
        function toggleClusterDetails(clusterId) {{
            const detailsRow = document.getElementById('details-' + clusterId);
            const icon = document.getElementById('icon-' + clusterId);
            
            if (detailsRow.classList.contains('show')) {{
                detailsRow.classList.remove('show');
                icon.textContent = '▶';
            }} else {{
                // Hide all other details first
                document.querySelectorAll('.cluster-details').forEach(row => {{
                    row.classList.remove('show');
                }});
                document.querySelectorAll('.expand-icon').forEach(icon => {{
                    icon.textContent = '▶';
                }});
                
                // Show current details
                detailsRow.classList.add('show');
                icon.textContent = '▼';
            }}
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>EKS Upgrade Assessment Report</h1>
        <p>Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-value">{len(clusters_data)}</div>
                <div class="summary-label">Total Clusters</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{sum(1 for c in clusters_data.values() if c.get('cluster_status') == 'ACTIVE')}</div>
                <div class="summary-label">Active Clusters</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{sum(len(c.get('node_groups', [])) for c in clusters_data.values())}</div>
                <div class="summary-label">Total Node Groups</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{sum(1 for c in clusters_data.values() if c.get('karpenter', {}).get('installed'))}</div>
                <div class="summary-label">With Karpenter</div>
            </div>
        </div>
        
        <h2>Cluster Overview</h2>
        <p><em>Click on any cluster row to view detailed information</em></p>
        <table>
            <thead>
                <tr>
                    <th>Cluster Name</th>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Node Groups</th>
                    <th>Fargate</th>
                    <th>Addons</th>
                    <th>Karpenter</th>
                    <th>AWS Plugins</th>
                    <th>Created</th>
                </tr>
            </thead>
            <tbody>
"""
        
        cluster_index = 0
        for cluster_name, cluster_data in clusters_data.items():
            status_class = f"status-{cluster_data.get('cluster_status', '').lower()}"
            created_date = cluster_data.get('created_at', '').split('T')[0] if cluster_data.get('created_at') else 'N/A'
            
            # Karpenter info
            karpenter = cluster_data.get('karpenter', {})
            if karpenter.get('installed'):
                node_pools = karpenter.get('node_pools_count', 0)
                provisioners = karpenter.get('provisioners_count', 0)
                if node_pools > 0:
                    karpenter_status = f"✅ {node_pools} pools"
                elif provisioners > 0:
                    karpenter_status = f"✅ {provisioners} provisioners"
                else:
                    karpenter_status = "✅ Installed"
            else:
                karpenter_status = "❌ Not Installed"
            
            # AWS Plugins info - derive from addons to avoid duplication
            addons = cluster_data.get('addons', [])
            plugin_list = []
            for addon in addons:
                addon_name = addon.get('name', '')
                if 'load-balancer-controller' in addon_name or 'alb' in addon_name.lower():
                    plugin_list.append('ALB')
                elif 'cluster-autoscaler' in addon_name:
                    plugin_list.append('CA')
                elif 'ebs-csi' in addon_name:
                    plugin_list.append('EBS')
                elif 'efs-csi' in addon_name:
                    plugin_list.append('EFS')
            
            plugins_display = ', '.join(plugin_list) if plugin_list else "Core only"
            
            html_content += f"""
                <tr class="cluster-row" onclick="toggleClusterDetails('{cluster_index}')">
                    <td><strong>{cluster_name}</strong><span class="expand-icon" id="icon-{cluster_index}">▶</span></td>
                    <td>{cluster_data.get('cluster_version', 'N/A')}</td>
                    <td><span class="{status_class}">{cluster_data.get('cluster_status', 'N/A')}</span></td>
                    <td>{len(cluster_data.get('node_groups', []))}</td>
                    <td>{len(cluster_data.get('fargate_profiles', []))}</td>
                    <td>{len(cluster_data.get('addons', []))}</td>
                    <td>{karpenter_status}</td>
                    <td>{plugins_display}</td>
                    <td>{created_date}</td>
                </tr>
                <tr class="cluster-details" id="details-{cluster_index}">
                    <td colspan="9">
                        <div class="details-content">
                            <div class="details-grid">
"""
            
            # Node Groups Details
            html_content += """
                                <div class="details-section">
                                    <h4>Node Groups</h4>
                                    <table class="details-table">
                                        <thead>
                                            <tr>
                                                <th>Name</th>
                                                <th>Status</th>
                                                <th>Version</th>
                                                <th>Capacity Type</th>
                                                <th>Instance Types</th>
                                                <th>AMI Type</th>
                                            </tr>
                                        </thead>
                                        <tbody>
"""
            node_groups = cluster_data.get('node_groups', [])
            if node_groups:
                for ng in node_groups:
                    instance_types = ', '.join(ng.get('instance_types', [])[:2])
                    if len(ng.get('instance_types', [])) > 2:
                        instance_types += f" (+{len(ng.get('instance_types', [])) - 2} more)"
                    
                    ng_status_class = f"status-{ng.get('status', '').lower()}"
                    html_content += f"""
                                            <tr>
                                                <td><strong>{ng.get('name', 'N/A')}</strong></td>
                                                <td><span class="{ng_status_class}">{ng.get('status', 'N/A')}</span></td>
                                                <td>{ng.get('version', 'N/A')}</td>
                                                <td><span class="badge badge-info">{ng.get('capacity_type', 'N/A')}</span></td>
                                                <td>{instance_types}</td>
                                                <td>{ng.get('ami_type', 'N/A')}</td>
                                            </tr>
"""
            else:
                html_content += '<tr><td colspan="6">No node groups found</td></tr>'
            
            html_content += """
                                        </tbody>
                                    </table>
                                </div>
"""
            
            # EKS Addons Details
            html_content += """
                                <div class="details-section">
                                    <h4>EKS Addons</h4>
                                    <table class="details-table">
                                        <thead>
                                            <tr>
                                                <th>Name</th>
                                                <th>Version</th>
                                                <th>Status</th>
                                                <th>Type</th>
                                            </tr>
                                        </thead>
                                        <tbody>
"""
            addons = cluster_data.get('addons', [])
            if addons:
                for addon in addons:
                    core_addons = ['vpc-cni', 'coredns', 'kube-proxy']
                    addon_type = "Core" if addon.get('name') in core_addons else "Additional"
                    badge_class = "badge-success" if addon.get('name') in core_addons else "badge-primary"
                    addon_status_class = f"status-{addon.get('status', '').lower()}"
                    
                    html_content += f"""
                                            <tr>
                                                <td><strong>{addon.get('name', 'N/A')}</strong></td>
                                                <td>{addon.get('version', 'N/A')}</td>
                                                <td><span class="{addon_status_class}">{addon.get('status', 'N/A')}</span></td>
                                                <td><span class="badge {badge_class}">{addon_type}</span></td>
                                            </tr>
"""
            else:
                html_content += '<tr><td colspan="4">No addons found</td></tr>'
            
            html_content += """
                                        </tbody>
                                    </table>
                                </div>
"""
            
            # Karpenter Details
            html_content += """
                                <div class="details-section">
                                    <h4>Karpenter</h4>
                                    <table class="details-table">
                                        <thead>
                                            <tr>
                                                <th>Component</th>
                                                <th>Status</th>
                                                <th>Count</th>
                                                <th>Version</th>
                                            </tr>
                                        </thead>
                                        <tbody>
"""
            if karpenter.get('installed'):
                html_content += f"""
                                            <tr>
                                                <td><strong>Karpenter</strong></td>
                                                <td><span class="badge badge-success">Installed</span></td>
                                                <td>-</td>
                                                <td>{karpenter.get('version', 'N/A')}</td>
                                            </tr>
                                            <tr>
                                                <td>Node Pools</td>
                                                <td><span class="badge badge-info">Active</span></td>
                                                <td>{karpenter.get('node_pools_count', 0)}</td>
                                                <td>-</td>
                                            </tr>
"""
                if karpenter.get('provisioners_count', 0) > 0:
                    html_content += f"""
                                            <tr>
                                                <td>Provisioners (Legacy)</td>
                                                <td><span class="badge badge-warning">Legacy</span></td>
                                                <td>{karpenter.get('provisioners_count', 0)}</td>
                                                <td>-</td>
                                            </tr>
"""
            else:
                html_content += """
                                            <tr>
                                                <td><strong>Karpenter</strong></td>
                                                <td><span class="badge badge-warning">Not Installed</span></td>
                                                <td>-</td>
                                                <td>-</td>
                                            </tr>
"""
            
            html_content += """
                                        </tbody>
                                    </table>
                                </div>
"""
            
            # AWS Plugins Details - derive from addons
            html_content += """
                                <div class="details-section">
                                    <h4>AWS Plugins (from EKS Addons)</h4>
                                    <ul class="resource-list">
"""
            
            # Derive plugin info from addons
            addons = cluster_data.get('addons', [])
            plugin_checks = [
                ('AWS Load Balancer Controller', 'load-balancer-controller'),
                ('Cluster Autoscaler', 'cluster-autoscaler'),
                ('EBS CSI Driver', 'ebs-csi'),
                ('EFS CSI Driver', 'efs-csi')
            ]
            
            for plugin_name, addon_pattern in plugin_checks:
                installed = any(addon_pattern in addon.get('name', '') for addon in addons)
                status_badge = '<span class="badge badge-success">Installed</span>' if installed else '<span class="badge badge-warning">Not Installed</span>'
                html_content += f"""
                                        <li class="resource-item">
                                            <div><strong>{plugin_name}</strong></div>
                                            <div>{status_badge}</div>
                                        </li>
"""
            
            # Core addon versions - get VPC CNI from addons
            vpc_cni_addon = next((addon for addon in addons if 'vpc-cni' in addon.get('name', '')), None)
            if vpc_cni_addon:
                html_content += f"""
                                        <li class="resource-item">
                                            <div><strong>VPC CNI Version</strong></div>
                                            <div>{vpc_cni_addon.get('version', 'N/A')}</div>
                                        </li>
"""
            
            html_content += """
                                    </ul>
                                </div>
"""
            
            # Fargate Profiles Details
            html_content += """
                                <div class="details-section">
                                    <h4>Fargate Profiles</h4>
                                    <ul class="resource-list">
"""
            fargate_profiles = cluster_data.get('fargate_profiles', [])
            if fargate_profiles:
                for fp in fargate_profiles:
                    fp_status_class = f"status-{fp.get('status', '').lower()}"
                    html_content += f"""
                                        <li class="resource-item">
                                            <div><strong>{fp.get('name', 'N/A')}</strong></div>
                                            <div><span class="{fp_status_class}">{fp.get('status', 'N/A')}</span></div>
                                        </li>
"""
            else:
                html_content += '<li class="resource-item">No Fargate profiles found</li>'
            
            html_content += """
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </td>
                </tr>
"""
            
            cluster_index += 1
        
        html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        
        # Save HTML report
        html_report_path = Path(output_dir) / "01-pre-upgrade-assessment" / "assessment-report.html"
        with open(html_report_path, 'w') as f:
            f.write(html_content)
        
        print(f"✅ Generated HTML report: {html_report_path}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate HTML report: {str(e)}")

def generate_assessment_readme(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate main assessment README file."""
    readme_content = f"""# EKS Upgrade Assessment Report

## Overview
This assessment provides comprehensive analysis of your EKS clusters for upgrade readiness following AWS best practices.

**Target Region:** {config.aws_configuration.region}
**Assessment Date:** Generated on analysis run
**Clusters Assessed:** {len(cluster_analysis)}

## Assessment Summary
"""
    
    for cluster_name, analysis in cluster_analysis.items():
        cluster_info = analysis['cluster_info']
        insights = analysis.get('insights', [])
        kubent_results = analysis.get('kubent_results', {})
        pluto_results = analysis.get('pluto_results', {})
        
        # Determine overall assessment result
        has_critical_issues = (
            any(insight.get('insightStatus', {}).get('status') == 'ERROR' for insight in insights) or
            (kubent_results.get('status') == 'success' and len(kubent_results.get('deprecated_apis', [])) > 0) or
            (pluto_results.get('status') == 'success' and len(pluto_results.get('deprecated_apis', [])) > 0)
        )
        
        if has_critical_issues:
            assessment_result = "❌ NEEDS ATTENTION"
        else:
            assessment_result = "✅ READY FOR UPGRADE"
        
        readme_content += f"""
### {cluster_name}
- **Current Version:** {cluster_info.version}
- **Target Version:** {config.upgrade_targets.control_plane_target_version}
- **Status:** {cluster_info.status}
- **Assessment Result:** {assessment_result}
- **Node Groups:** {len(analysis['node_groups'])}
- **Fargate Profiles:** {len(analysis['fargate_profiles'])}
- **Addons:** {len(analysis['addons'])}
"""
    
    readme_content += """
## Assessment Structure

1. **[Assessment Reports](assessment-reports/)** - Detailed cluster readiness analysis
2. **[Cluster Metadata](cluster-metadata/)** - Complete cluster configuration data
3. **[Scripts](scripts/)** - Assessment validation and helper scripts
4. **[Web UI](web-ui/)** - Interactive assessment dashboard

## Key Findings

### Deprecated APIs
Review the assessment reports for any deprecated APIs that need attention before upgrade.

### Cluster Insights
EKS Cluster Insights findings are included in the detailed assessment reports.

### Resource Inventory
Complete AWS resource inventory is available for each cluster to understand dependencies.

## Next Steps

1. Review the detailed assessment reports in the `assessment-reports/` folder
2. Address any critical issues identified in the assessment
3. Plan your upgrade strategy based on the findings
4. Use the cluster metadata for upgrade planning and rollback preparation

## Important Notes

⚠️ **Assessment Scope**: This assessment focuses on upgrade readiness analysis only.

⚠️ **Deprecated APIs**: Pay special attention to any deprecated APIs that will be removed in the target Kubernetes version.

## Support

For detailed upgrade guidance, refer to the AWS EKS documentation and best practices guide.
"""
    
    with open(Path(output_dir, "README.md"), 'w') as f:
        f.write(readme_content)


def generate_cluster_metadata_json(cluster_analysis: dict, output_dir: str):
    """Generate comprehensive cluster metadata JSON file."""
    try:
        # Extract cluster metadata for JSON export
        clusters_metadata = {}
        for cluster_name, analysis in cluster_analysis.items():
            clusters_metadata[cluster_name] = analysis.get('cluster_metadata', {})
        
        # Save to assessment-reports directory
        metadata_file = Path(output_dir) / "assessment-reports" / "clusters-metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_file, 'w') as f:
            json.dump(clusters_metadata, f, indent=2, default=str)
        
        print(f"✅ Cluster metadata JSON saved to: {metadata_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate cluster metadata JSON: {str(e)}")


def generate_assessment_scripts(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate assessment validation scripts."""
    try:
        scripts_dir = Path(output_dir) / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate cluster validation script
        validation_script = f"""#!/bin/bash
# EKS Cluster Assessment Validation Script
# Generated for region: {config.aws_configuration.region}

set -e

REGION="{config.aws_configuration.region}"
CLUSTERS=({' '.join([f'"{name}"' for name in cluster_analysis.keys()])})

echo "✅ Running EKS cluster assessment validation..."

for CLUSTER in "${{CLUSTERS[@]}}"; do
    echo "Validating cluster: $CLUSTER"
    
    # Check cluster status
    echo "  🔍 Checking cluster status..."
    STATUS=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.status' --output text)
    VERSION=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.version' --output text)
    echo "    Cluster status: $STATUS"
    echo "    Cluster version: $VERSION"
    
    if [ "$STATUS" != "ACTIVE" ]; then
        echo "    ❌ Cluster is not in ACTIVE state!"
        continue
    fi
    
    # Check node groups
    echo "  🖥️  Checking node groups..."
    aws eks list-nodegroups --region $REGION --cluster-name $CLUSTER --query 'nodegroups' --output table
    
    # Check Fargate profiles
    echo "  🚀 Checking Fargate profiles..."
    aws eks list-fargate-profiles --region $REGION --cluster-name $CLUSTER --query 'fargateProfileNames' --output table
    
    # Check EKS add-ons
    echo "  🔧 Checking EKS add-ons..."
    aws eks list-addons --region $REGION --cluster-name $CLUSTER --output table
    
    echo "  ✅ Validation complete for $CLUSTER"
    echo ""
done

echo "✅ Assessment validation completed"
"""
        
        validation_script_file = scripts_dir / "assessment-validation.sh"
        with open(validation_script_file, 'w') as f:
            f.write(validation_script)
        
        # Make script executable
        validation_script_file.chmod(0o755)
        
        print(f"✅ Assessment validation script generated: {validation_script_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate assessment scripts: {str(e)}")


def get_status_emoji(status: str) -> str:
    """Convert status to emoji representation."""
    status_map = {
        'success': '✅ PASS',
        'failed': '❌ FAIL',
        'error': '❌ ERROR',
        'timeout': '⏰ TIMEOUT',
        'tool_not_found': '🔧 MISSING',
        'kubectl_not_configured': '⚙️ CONFIG',
        'not_run': '⏸️ SKIPPED',
        'skipped': '⏸️ SKIPPED',
        'parse_error': '📄 PARSE_ERROR'
    }
    return status_map.get(status, f'❓ {status.upper()}')


def generate_documentation(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate assessment documentation based on analysis."""
    # Create directory structure (output_dir now includes the full path)
    dirs_to_create = [
        "cluster-metadata", 
        "scripts",
        "web-ui"
    ]
    
    for dir_name in dirs_to_create:
        Path(output_dir, dir_name).mkdir(parents=True, exist_ok=True)
    
    # Step 1: Generate main README
    generate_assessment_readme(config, cluster_analysis, output_dir)
    
    # Step 2: Generate assessment reports and data first
    generate_assessment_reports(config, cluster_analysis, output_dir)
    
    # Step 3: Generate cluster metadata JSON
    generate_cluster_metadata_json(cluster_analysis, output_dir)
    
    # Step 4: Generate assessment scripts
    generate_assessment_scripts(config, cluster_analysis, output_dir)
    
    # Step 5: Generate web UI using the generated report data (last step)
    generate_web_ui_from_reports(cluster_analysis, output_dir)


def generate_main_readme(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate main README file."""
    readme_content = f"""# EKS Upgrade Instructions

## Overview
This documentation provides comprehensive instructions for upgrading your EKS clusters following AWS best practices.

**Target Region:** {config.aws_configuration.region}
**Upgrade Strategy:** {config.upgrade_strategy.method}
**Clusters to Upgrade:** {len(cluster_analysis)}

## Clusters Summary
"""
    
    for cluster_name, analysis in cluster_analysis.items():
        cluster_info = analysis['cluster_info']
        readme_content += f"""
### {cluster_name}
- **Current Version:** {cluster_info.version}
- **Target Version:** {config.upgrade_targets.control_plane_target_version}
- **Status:** {cluster_info.status}
- **Node Groups:** {len(analysis['node_groups'])}
- **Fargate Profiles:** {len(analysis['fargate_profiles'])}
- **Addons:** {len(analysis['addons'])}
"""
    
    readme_content += """
## Documentation Structure

1. **[Pre-upgrade Assessment](01-pre-upgrade-assessment/)** - Cluster readiness analysis
2. **[Backup and Preparation](02-backup-and-preparation/)** - Backup strategies and preparation steps
3. **[Upgrade Execution](03-upgrade-execution/)** - Step-by-step upgrade procedures
4. **[Post-upgrade Validation](04-post-upgrade-validation/)** - Validation and monitoring setup
5. **[Resilience Hub Integration](05-resilience-hub-integration/)** - Disaster recovery planning
6. **[Scripts](scripts/)** - Automated validation and helper scripts

## Quick Start

1. Review the pre-upgrade assessment reports
2. Follow the backup and preparation steps
3. Choose your upgrade strategy (in-place or blue-green)
4. Execute the upgrade following the detailed instructions
5. Validate the upgrade using the provided checklists and scripts

## Important Notes

⚠️ **Backup Limitations**: Velero can only restore to clusters running Kubernetes versions currently supported by EKS.

⚠️ **AWS Resources**: Many AWS resources are NOT backed up by Velero and require manual recreation. See the AWS resources inventory for details.

## Support

For issues or questions, refer to the AWS EKS documentation and best practices guide.
"""
    
    with open(Path(output_dir, "README.md"), 'w') as f:
        f.write(readme_content)





def parse_deprecated_api_metric(metric_line: str) -> dict:
    """Parse a deprecated API metric line into structured information."""
    import re
    
    # Parse the metric line: apiserver_requested_deprecated_apis{labels} value
    pattern = r'apiserver_requested_deprecated_apis\{([^}]+)\}\s+(\d+)'
    match = re.match(pattern, metric_line)
    
    if not match:
        return {
            'raw_metric': metric_line,
            'api_path': 'Unknown format',
            'resource': 'Unknown',
            'version': 'Unknown',
            'group': 'Unknown',
            'count': 'Unknown',
            'description': 'Could not parse metric format'
        }
    
    labels_str = match.group(1)
    count = match.group(2)
    
    # Parse labels
    labels = {}
    label_pattern = r'(\w+)="([^"]*)"'
    for label_match in re.finditer(label_pattern, labels_str):
        key, value = label_match.groups()
        labels[key] = value
    
    # Extract key information
    group = labels.get('group', '')
    version = labels.get('version', 'v1')
    resource = labels.get('resource', 'unknown')
    subresource = labels.get('subresource', '')
    
    # Build API path
    if group:
        api_path = f"/apis/{group}/{version}/{resource}"
    else:
        api_path = f"/api/{version}/{resource}"
    
    if subresource:
        api_path += f"/{subresource}"
    
    # Get description for common deprecated APIs
    descriptions = {
        'componentstatuses': 'Cluster component health status API - deprecated, use metrics and monitoring instead',
        'selfsubjectaccessreviews': 'Self subject access review API - check for newer authorization APIs',
        'selfsubjectrulesreviews': 'Self subject rules review API - check for newer authorization APIs',
        'localsubjectaccessreviews': 'Local subject access review API - check for newer authorization APIs',
        'subjectaccessreviews': 'Subject access review API - check for newer authorization APIs'
    }
    
    description = descriptions.get(resource, f'Deprecated {resource} API - review usage and update to newer version')
    
    return {
        'raw_metric': metric_line,
        'api_path': api_path,
        'resource': resource,
        'version': version,
        'group': group if group else 'core',
        'subresource': subresource,
        'count': count,
        'description': description,
        'removed_release': labels.get('removed_release', 'Not specified')
    }


def get_status_emoji(status: str) -> str:
    """Get emoji representation for status."""
    status_map = {
        'success': '✅ SUCCESS',
        'tool_not_found': '⚠️ TOOL_NOT_FOUND',
        'kubectl_not_configured': '⚠️ KUBECTL_NOT_CONFIGURED',
        'not_run': '⚠️ NOT_RUN',
        'skipped': '⚠️ SKIPPED',
        'scan_failed': '❌ FAILED',
        'parse_error': '❌ PARSE_ERROR',
        'timeout': '❌ TIMEOUT',
        'error': '❌ ERROR',
        'partial_failure': '⚠️ PARTIAL'
    }
    return status_map.get(status, '❓ UNKNOWN')


def generate_backup_docs(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate backup and preparation documentation."""
    backup_dir = Path(output_dir, "02-backup-and-preparation")
    
    # Generate backup strategy document
    strategy_content = f"""# Backup Strategy

## Strategy Selection
**Upgrade Method:** {config.upgrade_strategy.method}
**Backup Tool:** {config.resilience_requirements.backup_strategy}

## Backup Requirements by Strategy

### In-place Upgrade
- ✅ **Velero backup REQUIRED** - Essential for rollback capability
- ✅ **AWS resource documentation REQUIRED** - Critical for disaster recovery

### Blue-green Upgrade  
- ⚠️ **Velero backup OPTIONAL** - Original cluster remains available
- ✅ **AWS resource replication REQUIRED** - Focus on replicating to new cluster

## Critical Velero Limitations

⚠️ **EKS Version Support**: Velero can only restore to clusters running Kubernetes versions currently supported by EKS.

⚠️ **AWS Resources NOT Backed Up**: Velero does NOT backup AWS-managed resources. See aws-resources-inventory.md for complete list.

## Next Steps

1. Review AWS resources inventory for each cluster
2. Set up Velero (if using in-place upgrade)
3. Document all AWS resources for manual recreation
4. Test backup and restore procedures
"""
    
    with open(backup_dir / "backup-strategy.md", 'w') as f:
        f.write(strategy_content)
    
    # Generate AWS resource inventory for each cluster
    from utils.resource_inventory import ResourceInventoryGenerator
    
    for cluster_name, analysis in cluster_analysis.items():
        if 'resource_inventory' in analysis:
            inventory = analysis['resource_inventory']
            inventory_generator = ResourceInventoryGenerator(None)  # We already have the inventory
            inventory_md = inventory_generator.generate_inventory_markdown(inventory)
            
            # Write cluster-specific inventory
            inventory_filename = f"aws-resources-inventory-{cluster_name}.md"
            with open(backup_dir / inventory_filename, 'w') as f:
                f.write(inventory_md)
    
    # Generate Velero limitations document
    velero_limitations = """# Velero Backup Limitations

## Critical Understanding

Velero is a powerful backup tool for Kubernetes clusters, but it has important limitations when used with Amazon EKS.

## What Velero DOES Backup

✅ **Kubernetes Resources**:
- Deployments, Services, ConfigMaps, Secrets
- PersistentVolumeClaims (metadata only)
- Custom Resource Definitions (CRDs)
- RBAC configurations
- Namespaces and their contents

✅ **Application Data** (with proper configuration):
- Persistent volume snapshots (EBS, EFS with CSI drivers)
- Application-consistent backups

## What Velero DOES NOT Backup

❌ **EKS Control Plane**:
- Cluster configuration
- Control plane version
- Cluster endpoint and certificates
- OIDC identity provider

❌ **AWS Infrastructure**:
- VPC, subnets, security groups
- IAM roles and policies
- Load balancers and target groups
- Route53 DNS records

❌ **EKS-Specific Resources**:
- Node groups and launch templates
- Fargate profiles
- EKS add-ons configuration
- Cluster autoscaler settings

❌ **AWS Services Integration**:
- CloudWatch log groups and alarms
- Secrets Manager secrets
- Parameter Store parameters
- ECR repositories

## EKS Version Support Limitation

⚠️ **CRITICAL**: Velero can only restore to clusters running Kubernetes versions currently supported by EKS.

### Impact:
- If your current cluster version becomes unsupported by EKS, you cannot restore to a new cluster
- Always check EKS version support before relying on Velero for disaster recovery
- Plan upgrades before versions reach end-of-support

### Mitigation:
- Keep clusters on supported versions
- Test restore procedures regularly
- Maintain Infrastructure as Code (IaC) for AWS resources
- Document manual recreation procedures

## Best Practices

1. **Use Velero for application data and Kubernetes resources only**
2. **Maintain separate documentation/automation for AWS infrastructure**
3. **Test restore procedures in non-production environments**
4. **Keep Infrastructure as Code (Terraform/CloudFormation) up to date**
5. **Regular backup validation and cleanup**

## Recommended Backup Strategy

### For In-place Upgrades:
1. **Velero backup** - For application rollback capability
2. **AWS resource documentation** - For infrastructure recreation
3. **Application data snapshots** - For data protection

### For Blue-green Upgrades:
1. **AWS resource replication** - Focus on infrastructure recreation
2. **Application migration** - Direct data migration to new cluster
3. **Velero backup optional** - Original cluster remains available during transition
"""
    
    with open(backup_dir / "velero-limitations.md", 'w') as f:
        f.write(velero_limitations)


def generate_upgrade_docs(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate upgrade execution documentation."""
    upgrade_dir = Path(output_dir, "03-upgrade-execution")
    
    # Generate common preparation steps
    common_steps = """# Common Preparation Steps

These steps are required regardless of your chosen upgrade strategy (in-place or blue-green).

## 1. Pre-upgrade Validation
- [ ] Run cluster insights assessment
- [ ] Check for deprecated APIs using kubent/pluto
- [ ] Validate workload configurations
- [ ] Review PodDisruptionBudgets and topology constraints

## 2. Backup Preparation
- [ ] Document all AWS resources (see aws-resources-inventory.md)
- [ ] Export cluster configurations
- [ ] Backup application data
- [ ] Test restore procedures

## 3. Workload Preparation
- [ ] Update deprecated API usage
- [ ] Configure PodDisruptionBudgets
- [ ] Set up topology spread constraints
- [ ] Update container images if needed

## 4. Monitoring Setup
- [ ] Enable control plane logging
- [ ] Set up CloudWatch monitoring
- [ ] Configure alerting for upgrade process

## 5. Communication Plan
- [ ] Notify stakeholders of upgrade schedule
- [ ] Prepare rollback communication plan
- [ ] Document emergency contacts
"""
    
    with open(upgrade_dir / "common-preparation-steps.md", 'w') as f:
        f.write(common_steps)


def generate_validation_docs(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate validation documentation."""
    validation_dir = Path(output_dir, "04-post-upgrade-validation")
    
    validation_content = """# Post-upgrade Validation Checklist

## Control Plane Validation
- [ ] Verify cluster status is ACTIVE
- [ ] Check control plane version
- [ ] Validate API server accessibility
- [ ] Review control plane logs

## Data Plane Validation  
- [ ] Verify all nodes are Ready
- [ ] Check node group versions
- [ ] Validate Fargate profile functionality
- [ ] Test pod scheduling

## Workload Validation
- [ ] Verify all pods are running
- [ ] Test application functionality
- [ ] Check service connectivity
- [ ] Validate ingress/load balancer functionality

## Add-on Validation
- [ ] Verify EKS add-on versions
- [ ] Test CNI functionality
- [ ] Validate DNS resolution
- [ ] Check storage provisioning

## Monitoring and Logging
- [ ] Verify CloudWatch metrics
- [ ] Check control plane logs
- [ ] Validate application logs
- [ ] Test alerting functionality
"""
    
    with open(validation_dir / "validation-checklist.md", 'w') as f:
        f.write(validation_content)


def generate_scripts(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate helper scripts."""
    scripts_dir = Path(output_dir, "scripts")
    
    # Generate pre-upgrade check script
    check_script = f"""#!/bin/bash
# Pre-upgrade validation script

set -e

REGION="{config.aws_configuration.region}"
CLUSTERS=({' '.join([f'"{name}"' for name in cluster_analysis.keys()])})

echo "🔍 Running pre-upgrade checks..."

for CLUSTER in "${{CLUSTERS[@]}}"; do
    echo "Checking cluster: $CLUSTER"
    
    # Check cluster status
    STATUS=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.status' --output text)
    echo "  Cluster status: $STATUS"
    
    # Check cluster insights
    echo "  Running cluster insights check..."
    aws eks list-insights --region $REGION --cluster-name $CLUSTER
    
    # Check for deprecated APIs (requires kubent)
    if command -v kubent &> /dev/null; then
        echo "  Checking for deprecated APIs..."
        kubent --cluster-name $CLUSTER
    else
        echo "  ⚠️  kubent not found. Install kubent for deprecated API checking."
    fi
    
    echo "  ✅ Checks complete for $CLUSTER"
done

echo "✅ All pre-upgrade checks completed"
"""
    
    with open(scripts_dir / "pre-upgrade-checks.sh", 'w') as f:
        f.write(check_script)
    
    # Generate AWS resource inventory script
    inventory_script = f"""#!/bin/bash
# AWS Resource Inventory Script

set -e

REGION="{config.aws_configuration.region}"
CLUSTERS=({' '.join([f'"{name}"' for name in cluster_analysis.keys()])})

echo "📋 Generating AWS resource inventory..."

for CLUSTER in "${{CLUSTERS[@]}}"; do
    echo "Inventorying resources for cluster: $CLUSTER"
    
    echo "  📊 Load Balancers..."
    aws elbv2 describe-load-balancers --region $REGION --query "LoadBalancers[?contains(Tags[?Key==\`kubernetes.io/cluster/$CLUSTER\`], \`owned\`) || contains(Tags[?Key==\`kubernetes.io/cluster/$CLUSTER\`], \`shared\`)]" --output table
    
    echo "  🎯 Target Groups..."
    aws elbv2 describe-target-groups --region $REGION --query "TargetGroups[?contains(Tags[?Key==\`kubernetes.io/cluster/$CLUSTER\`], \`owned\`) || contains(Tags[?Key==\`kubernetes.io/cluster/$CLUSTER\`], \`shared\`)]" --output table
    
    echo "  💾 EBS Volumes (requires kubectl)..."
    if command -v kubectl &> /dev/null; then
        echo "    Getting persistent volumes..."
        kubectl get pv -o jsonpath='{{range .items[*]}}{{.spec.awsElasticBlockStore.volumeID}}{{\"\\n\"}}{{end}}' 2>/dev/null || echo "    No EBS volumes found or kubectl not configured"
    else
        echo "    ⚠️  kubectl not found. Install kubectl to discover EBS volumes."
    fi
    
    echo "  📁 EFS File Systems..."
    aws efs describe-file-systems --region $REGION --query "FileSystems[?contains(Tags[?Key==\`kubernetes.io/cluster/$CLUSTER\`], \`owned\`) || contains(Tags[?Key==\`kubernetes.io/cluster/$CLUSTER\`], \`shared\`)]" --output table
    
    echo "  📊 CloudWatch Log Groups..."
    aws logs describe-log-groups --region $REGION --log-group-name-prefix "/aws/eks/$CLUSTER" --output table
    aws logs describe-log-groups --region $REGION --log-group-name-prefix "/aws/containerinsights/$CLUSTER" --output table
    
    echo "  🔔 CloudWatch Alarms..."
    aws cloudwatch describe-alarms --region $REGION --query "MetricAlarms[?contains(MetricName, \`eks\`) || contains(AlarmName, \`$CLUSTER\`)]" --output table
    
    echo "  🐳 ECR Repositories..."
    aws ecr describe-repositories --region $REGION --output table
    
    echo "  ✅ Inventory complete for $CLUSTER"
    echo ""
done

echo "✅ AWS resource inventory completed"
echo ""
echo "📝 Next steps:"
echo "1. Review the output above and document any resources that need manual recreation"
echo "2. Export configurations for critical resources using Infrastructure as Code"
echo "3. Test backup and restore procedures before proceeding with upgrade"
"""
    
    with open(scripts_dir / "aws-resource-inventory.sh", 'w') as f:
        f.write(inventory_script)
    
    # Generate deprecated API scanner script
    api_scanner_script = f"""#!/bin/bash
# Deprecated API Scanner Script

set -e

REGION="{config.aws_configuration.region}"
CLUSTERS=({' '.join([f'"{name}"' for name in cluster_analysis.keys()])})

echo "🔍 Scanning for deprecated APIs..."

for CLUSTER in "${{CLUSTERS[@]}}"; do
    echo "Scanning cluster: $CLUSTER"
    
    # Check audit logs for deprecated API usage
    echo "  📋 Checking audit logs for deprecated APIs..."
    QUERY_ID=$(aws logs start-query \\
        --region $REGION \\
        --log-group-name /aws/eks/$CLUSTER/cluster \\
        --start-time $(date -u --date="-30 minutes" "+%s") \\
        --end-time $(date "+%s") \\
        --query-string 'fields @message | filter `annotations.k8s.io/deprecated`="true"' \\
        --query queryId --output text 2>/dev/null || echo "")
    
    if [ ! -z "$QUERY_ID" ]; then
        echo "    Query started (ID: $QUERY_ID), waiting for results..."
        sleep 10
        aws logs get-query-results --region $REGION --query-id $QUERY_ID
    else
        echo "    ⚠️  Could not query audit logs. Ensure audit logging is enabled."
    fi
    
    # Check metrics for deprecated API usage
    echo "  📊 Checking metrics for deprecated API usage..."
    if command -v kubectl &> /dev/null; then
        kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis || echo "    No deprecated API metrics found"
    else
        echo "    ⚠️  kubectl not found. Install kubectl to check API metrics."
    fi
    
    # Run kubent if available
    if command -v kubent &> /dev/null; then
        echo "  🔧 Running kubent scan..."
        kubent --cluster-name $CLUSTER || echo "    kubent scan completed with warnings"
    else
        echo "    ⚠️  kubent not found. Install kubent for comprehensive deprecated API scanning."
        echo "    Installation: https://github.com/doitintl/kube-no-trouble"
    fi
    
    # Run pluto if available
    if command -v pluto &> /dev/null; then
        echo "  🔧 Running pluto scan..."
        pluto detect-all-in-cluster || echo "    pluto scan completed with warnings"
    else
        echo "    ⚠️  pluto not found. Install pluto for additional deprecated API scanning."
        echo "    Installation: https://github.com/FairwindsOps/pluto"
    fi
    
    echo "  ✅ API scan complete for $CLUSTER"
    echo ""
done

echo "✅ Deprecated API scanning completed"
echo ""
echo "📝 Next steps:"
echo "1. Review any deprecated API usage found above"
echo "2. Update manifests to use supported API versions"
echo "3. Test updated manifests in a development environment"
echo "4. Re-run this scan to verify all issues are resolved"
"""
    
    with open(scripts_dir / "deprecated-api-scanner.sh", 'w') as f:
        f.write(api_scanner_script)
    
    # Generate post-upgrade validation script
    validation_script = f"""#!/bin/bash
# Post-upgrade Validation Script

set -e

REGION="{config.aws_configuration.region}"
CLUSTERS=({' '.join([f'"{name}"' for name in cluster_analysis.keys()])})

echo "✅ Running post-upgrade validation..."

for CLUSTER in "${{CLUSTERS[@]}}"; do
    echo "Validating cluster: $CLUSTER"
    
    # Check cluster status
    echo "  🔍 Checking cluster status..."
    STATUS=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.status' --output text)
    VERSION=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.version' --output text)
    echo "    Cluster status: $STATUS"
    echo "    Cluster version: $VERSION"
    
    if [ "$STATUS" != "ACTIVE" ]; then
        echo "    ❌ Cluster is not in ACTIVE state!"
        continue
    fi
    
    # Check node groups
    echo "  🖥️  Checking node groups..."
    aws eks list-nodegroups --region $REGION --cluster-name $CLUSTER --query 'nodegroups' --output table
    
    # Check Fargate profiles
    echo "  🚀 Checking Fargate profiles..."
    aws eks list-fargate-profiles --region $REGION --cluster-name $CLUSTER --query 'fargateProfileNames' --output table
    
    # Check EKS add-ons
    echo "  🔧 Checking EKS add-ons..."
    aws eks list-addons --region $REGION --cluster-name $CLUSTER --output table
    
    # Kubernetes validation (requires kubectl)
    if command -v kubectl &> /dev/null; then
        echo "  ☸️  Checking Kubernetes resources..."
        
        # Check nodes
        echo "    Checking nodes..."
        kubectl get nodes --show-labels || echo "    ⚠️  Could not get nodes"
        
        # Check system pods
        echo "    Checking system pods..."
        kubectl get pods -n kube-system || echo "    ⚠️  Could not get system pods"
        
        # Check DNS functionality
        echo "    Testing DNS resolution..."
        kubectl run dns-test --image=busybox --rm -it --restart=Never -- nslookup kubernetes.default || echo "    ⚠️  DNS test failed"
        
        # Check storage classes
        echo "    Checking storage classes..."
        kubectl get storageclass || echo "    ⚠️  Could not get storage classes"
        
    else
        echo "    ⚠️  kubectl not found. Install and configure kubectl for comprehensive validation."
    fi
    
    echo "  ✅ Validation complete for $CLUSTER"
    echo ""
done

echo "✅ Post-upgrade validation completed"
echo ""
echo "📝 Next steps:"
echo "1. Review any warnings or errors above"
echo "2. Test your applications thoroughly"
echo "3. Monitor cluster performance and stability"
echo "4. Update monitoring and alerting configurations"
"""
    
    with open(scripts_dir / "post-upgrade-validation.sh", 'w') as f:
        f.write(validation_script)
    
    # Make all scripts executable
    for script_file in ["pre-upgrade-checks.sh", "aws-resource-inventory.sh", "deprecated-api-scanner.sh", "post-upgrade-validation.sh"]:
        os.chmod(scripts_dir / script_file, 0o755)


if __name__ == '__main__':
    cli()
    """Generate main assessment README file."""
    readme_content = f"""# EKS Upgrade Assessment Report

## Overview
This assessment provides comprehensive analysis of your EKS clusters for upgrade readiness following AWS best practices.

**Target Region:** {config.aws_configuration.region}
**Assessment Date:** {json.dumps(None, default=str).replace('null', 'Generated on analysis run')}
**Clusters Assessed:** {len(cluster_analysis)}

## Assessment Summary
"""
    
    for cluster_name, analysis in cluster_analysis.items():
        cluster_info = analysis['cluster_info']
        insights = analysis.get('insights', [])
        kubent_results = analysis.get('kubent_results', {})
        pluto_results = analysis.get('pluto_results', {})
        
        # Determine overall assessment result
        has_critical_issues = (
            any(insight.get('insightStatus', {}).get('status') == 'ERROR' for insight in insights) or
            (kubent_results.get('status') == 'success' and len(kubent_results.get('deprecated_apis', [])) > 0) or
            (pluto_results.get('status') == 'success' and len(pluto_results.get('deprecated_apis', [])) > 0)
        )
        
        if has_critical_issues:
            assessment_result = "❌ NEEDS ATTENTION"
        else:
            assessment_result = "✅ READY FOR UPGRADE"
        
        readme_content += f"""
### {cluster_name}
- **Current Version:** {cluster_info.version}
- **Target Version:** {config.upgrade_targets.control_plane_target_version}
- **Status:** {cluster_info.status}
- **Assessment Result:** {assessment_result}
- **Node Groups:** {len(analysis['node_groups'])}
- **Fargate Profiles:** {len(analysis['fargate_profiles'])}
- **Addons:** {len(analysis['addons'])}
"""
    
    readme_content += """
## Assessment Structure

1. **[Assessment Reports](assessment-reports/)** - Detailed cluster readiness analysis
2. **[Cluster Metadata](cluster-metadata/)** - Complete cluster configuration data
3. **[Scripts](scripts/)** - Assessment validation and helper scripts
4. **[Web UI](web-ui/)** - Interactive assessment dashboard

## Key Findings

### Deprecated APIs
Review the assessment reports for any deprecated APIs that need attention before upgrade.

### Cluster Insights
EKS Cluster Insights findings are included in the detailed assessment reports.

### Resource Inventory
Complete AWS resource inventory is available for each cluster to understand dependencies.

## Next Steps

1. Review the detailed assessment reports in the `assessment-reports/` folder
2. Address any critical issues identified in the assessment
3. Plan your upgrade strategy based on the findings
4. Use the cluster metadata for upgrade planning and rollback preparation

## Important Notes

⚠️ **Assessment Scope**: This assessment focuses on upgrade readiness analysis only.

⚠️ **Deprecated APIs**: Pay special attention to any deprecated APIs that will be removed in the target Kubernetes version.

## Support

For detailed upgrade guidance, refer to the AWS EKS documentation and best practices guide.
"""
    
    with open(Path(output_dir, "README.md"), 'w') as f:
        f.write(readme_content)


def generate_cluster_metadata_json(cluster_analysis: dict, output_dir: str):
    """Generate comprehensive cluster metadata JSON file."""
    try:
        # Extract cluster metadata for JSON export
        clusters_metadata = {}
        for cluster_name, analysis in cluster_analysis.items():
            clusters_metadata[cluster_name] = analysis.get('cluster_metadata', {})
        
        # Save to assessment-reports directory
        metadata_file = Path(output_dir) / "assessment-reports" / "clusters-metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_file, 'w') as f:
            json.dump(clusters_metadata, f, indent=2, default=str)
        
        print(f"✅ Cluster metadata JSON saved to: {metadata_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate cluster metadata JSON: {str(e)}")


def generate_assessment_scripts(config: EKSUpgradeConfig, cluster_analysis: dict, output_dir: str):
    """Generate assessment validation scripts."""
    try:
        scripts_dir = Path(output_dir) / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate cluster validation script
        validation_script = f"""#!/bin/bash
# EKS Cluster Assessment Validation Script
# Generated for region: {config.aws_configuration.region}

set -e

REGION="{config.aws_configuration.region}"
CLUSTERS=({' '.join([f'"{name}"' for name in cluster_analysis.keys()])})

echo "✅ Running EKS cluster assessment validation..."

for CLUSTER in "${{CLUSTERS[@]}}"; do
    echo "Validating cluster: $CLUSTER"
    
    # Check cluster status
    echo "  🔍 Checking cluster status..."
    STATUS=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.status' --output text)
    VERSION=$(aws eks describe-cluster --region $REGION --name $CLUSTER --query 'cluster.version' --output text)
    echo "    Cluster status: $STATUS"
    echo "    Cluster version: $VERSION"
    
    if [ "$STATUS" != "ACTIVE" ]; then
        echo "    ❌ Cluster is not in ACTIVE state!"
        continue
    fi
    
    # Check node groups
    echo "  🖥️  Checking node groups..."
    aws eks list-nodegroups --region $REGION --cluster-name $CLUSTER --query 'nodegroups' --output table
    
    # Check Fargate profiles
    echo "  🚀 Checking Fargate profiles..."
    aws eks list-fargate-profiles --region $REGION --cluster-name $CLUSTER --query 'fargateProfileNames' --output table
    
    # Check EKS add-ons
    echo "  🔧 Checking EKS add-ons..."
    aws eks list-addons --region $REGION --cluster-name $CLUSTER --output table
    
    # Kubernetes validation (requires kubectl)
    if command -v kubectl &> /dev/null; then
        echo "  ☸️  Checking Kubernetes resources..."
        
        # Configure kubectl for this cluster
        aws eks update-kubeconfig --region $REGION --name $CLUSTER
        
        # Check nodes
        echo "    Checking nodes..."
        kubectl get nodes --show-labels || echo "    ⚠️  Could not get nodes"
        
        # Check system pods
        echo "    Checking system pods..."
        kubectl get pods -n kube-system || echo "    ⚠️  Could not get system pods"
        
        # Test basic connectivity
        echo "    Testing cluster connectivity..."
        kubectl cluster-info || echo "    ⚠️  Cluster connectivity test failed"
        
    else
        echo "    ⚠️  kubectl not found. Install kubectl for comprehensive validation."
    fi
    
    echo "  ✅ Validation complete for $CLUSTER"
    echo ""
done

echo "✅ Assessment validation completed"
echo ""
echo "📝 Next steps:"
echo "1. Review any warnings or errors above"
echo "2. Run comprehensive assessment with the toolkit"
echo "3. Analyze deprecated API usage"
echo "4. Review cluster metadata and configuration"
"""
        
        validation_script_file = scripts_dir / "assessment-validation.sh"
        with open(validation_script_file, 'w') as f:
            f.write(validation_script)
        
        # Make script executable
        validation_script_file.chmod(0o755)
        
        print(f"✅ Assessment validation script generated: {validation_script_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate assessment scripts: {str(e)}")


def get_status_emoji(status: str) -> str:
    """Convert status to emoji representation."""
    status_map = {
        'success': '✅ PASS',
        'failed': '❌ FAIL',
        'error': '❌ ERROR',
        'timeout': '⏰ TIMEOUT',
        'tool_not_found': '🔧 MISSING',
        'kubectl_not_configured': '⚙️ CONFIG',
        'not_run': '⏸️ SKIPPED',
        'skipped': '⏸️ SKIPPED',
        'parse_error': '📄 PARSE_ERROR'
    }
    return status_map.get(status, f'❓ {status.upper()}')


if __name__ == '__main__':
    cli()
    """Generate web UI inside assessment-reports using the generated report data."""
    try:
        # Create web UI directory inside assessment-reports
        web_ui_dir = Path(output_dir) / "assessment-reports" / "web-ui"
        web_ui_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Extract assessment data from cluster analysis
        assessment_data = {}
        for cluster_name, analysis in cluster_analysis.items():
            cluster_info = analysis.get('cluster_info', {})
            insights = analysis.get('insights', [])
            kubent_results = analysis.get('kubent_results', {})
            pluto_results = analysis.get('pluto_results', {})
            cluster_metadata = analysis.get('cluster_metadata', {})
            
            # Create comprehensive assessment data for web UI
            assessment_data[cluster_name] = {
                'cluster_info': {
                    'name': cluster_name,
                    'version': cluster_info.version if hasattr(cluster_info, 'version') else 'Unknown',
                    'status': cluster_info.status if hasattr(cluster_info, 'status') else 'Unknown',
                    'endpoint': cluster_info.endpoint if hasattr(cluster_info, 'endpoint') else 'Unknown'
                },
                'assessment_results': {
                    'insights': {
                        'status': determine_insights_status(insights),
                        'count': len(insights),
                        'critical_issues': len([i for i in insights if i.get('insightStatus', {}).get('status') == 'ERROR']),
                        'warning_issues': len([i for i in insights if i.get('insightStatus', {}).get('status') == 'WARNING']),
                        'findings': insights[:5]  # Limit for web UI
                    },
                    'deprecated_apis': {
                        'kubent': {
                            'status': kubent_results.get('status', 'not_run'),
                            'count': len(kubent_results.get('deprecated_apis', [])),
                            'apis': kubent_results.get('deprecated_apis', [])[:10]  # Limit for web UI
                        },
                        'pluto': {
                            'status': pluto_results.get('status', 'not_run'),
                            'count': len(pluto_results.get('deprecated_apis', [])),
                            'apis': pluto_results.get('deprecated_apis', [])[:10]  # Limit for web UI
                        }
                    },
                    'addon_compatibility': analysis.get('addon_compatibility', {}),
                    'addon_iam_analysis': analysis.get('addon_iam_analysis', {})
                },
                'cluster_metadata': {
                    'node_groups': len(cluster_metadata.get('node_groups', [])),
                    'fargate_profiles': len(cluster_metadata.get('fargate_profiles', [])),
                    'addons': len(cluster_metadata.get('addons', [])),
                    'karpenter_installed': cluster_metadata.get('karpenter', {}).get('installed', False)
                    # Removed aws_plugins - plugin information is available in addons
                }
            }
        
        # Step 2: Save assessment data JSON for web UI
        assessment_data_file = web_ui_dir / "assessment-data.json"
        with open(assessment_data_file, 'w') as f:
            json.dump(assessment_data, f, indent=2, default=str)
        
        # Step 3: Generate standalone HTML dashboard
        html_content = generate_assessment_dashboard_html(assessment_data)
        
        # Step 4: Save HTML dashboard
        html_file = web_ui_dir / "index.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        # Step 5: Create simple CSS file
        css_content = """
/* EKS Assessment Dashboard Styles */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
    color: #333;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    background: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header {
    text-align: center;
    margin-bottom: 40px;
    padding-bottom: 20px;
    border-bottom: 2px solid #0073bb;
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin: 30px 0;
}

.summary-card {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    padding: 25px;
    border-radius: 8px;
    border-left: 4px solid #0073bb;
    text-align: center;
}

.summary-value {
    font-size: 2.5em;
    font-weight: bold;
    color: #0073bb;
    margin-bottom: 10px;
}

.summary-label {
    color: #666;
    font-size: 1.1em;
}

.cluster-section {
    margin: 40px 0;
    padding: 25px;
    border: 1px solid #ddd;
    border-radius: 8px;
    background: #fafafa;
}

.cluster-title {
    color: #232f3e;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #ddd;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin: 20px 0;
}

.status-item {
    background: white;
    padding: 15px;
    border-radius: 6px;
    border-left: 3px solid #28a745;
}

.status-item.warning {
    border-left-color: #ffc107;
}

.status-item.error {
    border-left-color: #dc3545;
}

.status-value {
    font-size: 1.5em;
    font-weight: bold;
    margin-bottom: 5px;
}

.status-label {
    color: #666;
    font-size: 0.9em;
}

.findings-list {
    background: white;
    padding: 20px;
    border-radius: 6px;
    margin: 20px 0;
}

.finding-item {
    padding: 10px;
    margin: 10px 0;
    border-left: 3px solid #17a2b8;
    background: #f8f9fa;
}

.finding-item.critical {
    border-left-color: #dc3545;
    background: #f8d7da;
}

.footer {
    text-align: center;
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #ddd;
    color: #666;
}
"""
        
        css_file = web_ui_dir / "styles.css"
        with open(css_file, 'w') as f:
            f.write(css_content)
        
        print(f"✅ Web UI dashboard generated: {html_file}")
        print(f"✅ Assessment data saved: {assessment_data_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not generate web UI from reports: {str(e)}")


def generate_assessment_dashboard_html(assessment_data: dict) -> str:
    """Generate HTML content for the assessment dashboard."""
    
    # Calculate summary statistics
    total_clusters = len(assessment_data)
    clusters_with_issues = 0
    total_deprecated_apis = 0
    total_critical_insights = 0
    
    for cluster_name, data in assessment_data.items():
        insights = data.get('assessment_results', {}).get('insights', {})
        kubent = data.get('assessment_results', {}).get('deprecated_apis', {}).get('kubent', {})
        pluto = data.get('assessment_results', {}).get('deprecated_apis', {}).get('pluto', {})
        
        critical_issues = insights.get('critical_issues', 0)
        deprecated_count = kubent.get('count', 0) + pluto.get('count', 0)
        
        if critical_issues > 0 or deprecated_count > 0:
            clusters_with_issues += 1
        
        total_deprecated_apis += deprecated_count
        total_critical_insights += critical_issues
    
    # Generate cluster sections HTML
    cluster_sections = ""
    for cluster_name, data in assessment_data.items():
        cluster_info = data.get('cluster_info', {})
        assessment_results = data.get('assessment_results', {})
        metadata = data.get('cluster_metadata', {})
        
        insights = assessment_results.get('insights', {})
        kubent = assessment_results.get('deprecated_apis', {}).get('kubent', {})
        pluto = assessment_results.get('deprecated_apis', {}).get('pluto', {})
        
        # Determine overall status
        critical_issues = insights.get('critical_issues', 0)
        deprecated_count = kubent.get('count', 0) + pluto.get('count', 0)
        
        if critical_issues > 0 or deprecated_count > 0:
            status_class = "error"
            status_text = "❌ NEEDS ATTENTION"
        else:
            status_class = ""
            status_text = "✅ READY"
        
        cluster_sections += f"""
        <div class="cluster-section">
            <h2 class="cluster-title">{cluster_name} - {status_text}</h2>
            
            <div class="status-grid">
                <div class="status-item">
                    <div class="status-value">{cluster_info.get('version', 'Unknown')}</div>
                    <div class="status-label">Kubernetes Version</div>
                </div>
                <div class="status-item">
                    <div class="status-value">{cluster_info.get('status', 'Unknown')}</div>
                    <div class="status-label">Cluster Status</div>
                </div>
                <div class="status-item {'warning' if critical_issues > 0 else ''}">
                    <div class="status-value">{critical_issues}</div>
                    <div class="status-label">Critical Insights</div>
                </div>
                <div class="status-item {'warning' if deprecated_count > 0 else ''}">
                    <div class="status-value">{deprecated_count}</div>
                    <div class="status-label">Deprecated APIs</div>
                </div>
                <div class="status-item">
                    <div class="status-value">{metadata.get('node_groups', 0)}</div>
                    <div class="status-label">Node Groups</div>
                </div>
                <div class="status-item">
                    <div class="status-value">{metadata.get('addons', 0)}</div>
                    <div class="status-label">EKS Add-ons</div>
                </div>
            </div>
            
            {generate_findings_section(insights, kubent, pluto)}
        </div>
        """
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EKS Upgrade Assessment Dashboard</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 EKS Upgrade Assessment Dashboard</h1>
            <p>Comprehensive analysis of your EKS clusters for upgrade readiness</p>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-value">{total_clusters}</div>
                <div class="summary-label">Total Clusters</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{clusters_with_issues}</div>
                <div class="summary-label">Clusters Need Attention</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{total_critical_insights}</div>
                <div class="summary-label">Critical Insights</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{total_deprecated_apis}</div>
                <div class="summary-label">Deprecated APIs Found</div>
            </div>
        </div>
        
        {cluster_sections}
        
        <div class="footer">
            <p>Generated by EKS Upgrade Assessment Toolkit | AWS Best Practices</p>
            <p>Review the detailed assessment reports and cluster metadata for complete analysis</p>
        </div>
    </div>
</body>
</html>
    """
    
    return html_content


def generate_findings_section(insights: dict, kubent: dict, pluto: dict) -> str:
    """Generate HTML for findings section."""
    findings_html = ""
    
    # EKS Insights findings
    if insights.get('findings'):
        findings_html += """
        <div class="findings-list">
            <h3>🔍 EKS Cluster Insights</h3>
        """
        for finding in insights['findings'][:3]:  # Show top 3
            status = finding.get('insightStatus', {}).get('status', 'INFO')
            css_class = 'critical' if status == 'ERROR' else ''
            findings_html += f"""
            <div class="finding-item {css_class}">
                <strong>{finding.get('name', 'Unknown')}</strong><br>
                <small>Status: {status} | Category: {finding.get('category', 'General')}</small>
            </div>
            """
        findings_html += "</div>"
    
    # Deprecated APIs findings
    if kubent.get('apis') or pluto.get('apis'):
        findings_html += """
        <div class="findings-list">
            <h3>⚠️ Deprecated APIs</h3>
        """
        
        # Kubent findings
        for api in kubent.get('apis', [])[:3]:  # Show top 3
            findings_html += f"""
            <div class="finding-item warning">
                <strong>kubent:</strong> {api.get('name', 'Unknown API')}<br>
                <small>Kind: {api.get('kind', 'Unknown')} | Version: {api.get('version', 'Unknown')}</small>
            </div>
            """
        
        # Pluto findings  
        for api in pluto.get('apis', [])[:3]:  # Show top 3
            findings_html += f"""
            <div class="finding-item warning">
                <strong>pluto:</strong> {api.get('name', 'Unknown API')}<br>
                <small>Kind: {api.get('kind', 'Unknown')} | Version: {api.get('version', 'Unknown')}</small>
            </div>
            """
        
        findings_html += "</div>"
    
    return findings_html
