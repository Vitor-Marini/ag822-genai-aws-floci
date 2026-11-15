# Uso: source env.sh  (vale só para o terminal atual)
_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_CONFIG_FILE="$_dir/tools/aws-config"            # isola de qualquer ~/.aws real
export AWS_SHARED_CREDENTIALS_FILE="$_dir/tools/aws-credentials"
export UV_CACHE_DIR="$_dir/tools/uv-cache" UV_PYTHON_INSTALL_DIR="$_dir/tools/uv-python"
export PATH="$_dir/tools/bin:$PATH"
[ -f "$_dir/.venv/bin/activate" ] && source "$_dir/.venv/bin/activate"
unset _dir
