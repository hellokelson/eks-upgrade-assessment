#!/bin/bash

# Demo script for NodeGroups Enhancement
# Shows the new Managed and IAM Role columns with enhanced copy functionality

echo "🚀 EKS Upgrade Assessment Toolkit - Enhanced NodeGroups Demo"
echo "=========================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Please run this script from the eks-upgrade-assessment directory"
    exit 1
fi

echo "📋 This demo showcases the enhanced NodeGroups features:"
echo "   1. 'Managed' column - Shows if node group is EKS-managed or self-managed"
echo "   2. 'IAM Role' column - Enhanced display with copy functionality"
echo ""
echo "🆕 NEW FEATURES:"
echo "   • Text wrapping for long IAM role ARNs"
echo "   • Copy-to-clipboard button (📋) for each IAM role"
echo "   • Visual feedback when copying (button turns green)"
echo "   • Two-line display: role name + full ARN"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

echo "🔍 Running assessment to generate demo data..."
echo ""

# Run the assessment
python src/main.py analyze --output-dir demo-enhanced-nodegroups-$(date +%Y%m%d-%H%M%S)

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Assessment completed successfully!"
    echo ""
    echo "🎯 To see the Enhanced NodeGroups features:"
    echo "   1. Open the generated web dashboard (index.html)"
    echo "   2. Click on any cluster to expand details"
    echo "   3. Navigate to the 'Node Groups' tab under 'Cluster Infrastructure'"
    echo "   4. Observe the enhanced 'IAM Role' column with copy functionality"
    echo ""
    echo "📊 Enhanced IAM Role Display Features:"
    echo "   • Role Name: Displayed prominently at the top"
    echo "   • Full ARN: Shown below with proper text wrapping"
    echo "   • Copy Button: Click the 📋 icon to copy full ARN"
    echo "   • Visual Feedback: Button turns green with 'Copied!' tooltip"
    echo "   • Responsive: Adapts to different screen sizes"
    echo ""
    echo "🔧 How to use the copy feature:"
    echo "   1. Find any IAM role in the NodeGroups table"
    echo "   2. Click the copy button (📋) next to the role"
    echo "   3. Watch for the green confirmation"
    echo "   4. Paste the full ARN anywhere you need it"
    echo ""
    
    # Find the latest assessment directory
    LATEST_DIR=$(ls -td demo-enhanced-nodegroups-* 2>/dev/null | head -1)
    if [ -n "$LATEST_DIR" ]; then
        echo "📁 Assessment saved to: $LATEST_DIR"
        echo "🌐 Open dashboard: open $LATEST_DIR/web-ui/index.html"
        echo ""
        
        # Offer to open the dashboard
        read -p "🚀 Would you like to open the web dashboard now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            open "$LATEST_DIR/web-ui/index.html"
            echo "✅ Dashboard opened in your default browser"
            echo ""
            echo "💡 Try the copy functionality:"
            echo "   • Navigate to any cluster's NodeGroups tab"
            echo "   • Click the 📋 button next to an IAM role"
            echo "   • The full ARN will be copied to your clipboard!"
        fi
    fi
else
    echo "❌ Assessment failed. Please check the error messages above."
    exit 1
fi

echo ""
echo "📖 For detailed documentation, see: NODEGROUPS_ENHANCEMENT.md"
echo "🎉 Enhanced NodeGroups demo completed!"
