# Repository-owned Linux shell bootstrap. macOS is deliberately excluded.
[[ "$OSTYPE" == linux* ]] || return
export MISE_GLOBAL_CONFIG_FILE="${${(%):-%N}:A:h}/mise.toml"
export MISE_INSTALL_MISSING_TOOLS=0
export MISE_NOT_FOUND_AUTO_INSTALL=0
# Remove inherited manager paths, keeping other application/user PATH entries.
typeset -a _mcp_mise_path
_mcp_mise_path=()
for _mcp_mise_item in "${path[@]}"; do
  case "$_mcp_mise_item" in
    "$HOME/.local/share/fnm"|"$HOME/.local/share/fnm/"*|/run/user/*/fnm_multishells/*|"$HOME/.bun/bin"|"$HOME/.local/share/mise/shims") ;;
    *) _mcp_mise_path+=("$_mcp_mise_item") ;;
  esac
done
path=("$HOME/.local/bin" "${_mcp_mise_path[@]}")
unset FNM_PATH FNM_DIR FNM_MULTISHELL_PATH FNM_NODE_DIST_MIRROR FNM_VERSION_FILE_STRATEGY BUN_INSTALL
eval "$("$HOME/.local/bin/mise" activate zsh)"
# UV's explicit invocation profile selects development Python without replacing OS Python.
uv() { "$HOME/.local/bin/uv" "$@"; }
uvx() { "$HOME/.local/bin/uvx" "$@"; }
unset _mcp_mise_path _mcp_mise_item
