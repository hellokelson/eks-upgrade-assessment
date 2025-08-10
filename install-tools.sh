#!/bin/bash
# Install required tools for EKS upgrade assessment

set -e

echo "🔧 Installing EKS upgrade assessment tools..."

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Map architecture names
case $ARCH in
    x86_64)
        ARCH="amd64"
        ;;
    aarch64|arm64)
        ARCH="arm64"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

echo "Detected OS: $OS, Architecture: $ARCH"

# Create tools directory
TOOLS_DIR="$HOME/.local/bin"
mkdir -p "$TOOLS_DIR"

# Add to PATH if not already there
if [[ ":$PATH:" != *":$TOOLS_DIR:"* ]]; then
    echo "export PATH=\"$TOOLS_DIR:\$PATH\"" >> ~/.bashrc
    export PATH="$TOOLS_DIR:$PATH"
    echo "✅ Added $TOOLS_DIR to PATH"
fi

# Install kubent
echo "📦 Installing kubent..."
KUBENT_VERSION="0.7.0"
KUBENT_URL="https://github.com/doitintl/kube-no-trouble/releases/download/${KUBENT_VERSION}/kubent-${KUBENT_VERSION}-${OS}-${ARCH}.tar.gz"

curl -L "$KUBENT_URL" -o /tmp/kubent.tar.gz
tar -xzf /tmp/kubent.tar.gz -C /tmp
mv /tmp/kubent "$TOOLS_DIR/"
chmod +x "$TOOLS_DIR/kubent"
rm -f /tmp/kubent.tar.gz

echo "✅ kubent installed successfully"

# Install pluto
echo "📦 Installing pluto..."
PLUTO_VERSION="5.19.0"
PLUTO_URL="https://github.com/FairwindsOps/pluto/releases/download/v${PLUTO_VERSION}/pluto_${PLUTO_VERSION}_${OS}_${ARCH}.tar.gz"

curl -L "$PLUTO_URL" -o /tmp/pluto.tar.gz
tar -xzf /tmp/pluto.tar.gz -C /tmp
mv /tmp/pluto "$TOOLS_DIR/"
chmod +x "$TOOLS_DIR/pluto"
rm -f /tmp/pluto.tar.gz

echo "✅ pluto installed successfully"

# Verify installations
echo "🔍 Verifying installations..."

if command -v kubent &> /dev/null; then
    echo "✅ kubent version: $(kubent --version)"
else
    echo "❌ kubent installation failed"
    exit 1
fi

if command -v pluto &> /dev/null; then
    echo "✅ pluto version: $(pluto version)"
else
    echo "❌ pluto installation failed"
    exit 1
fi

echo ""
echo "🎉 All tools installed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Restart your terminal or run: source ~/.bashrc"
echo "2. Verify tools are in PATH: kubent --version && pluto version"
echo "3. Configure kubectl for your EKS clusters"
echo "4. Run the EKS upgrade assessment: python src/main.py analyze"