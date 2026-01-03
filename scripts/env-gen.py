#!/usr/bin/env python3
"""
Environment Setup Script
Generates .env files for any directory that contains a .env.example file.
"""

import sys
from pathlib import Path
from typing import Dict, Optional

# Check if running in interactive mode
def is_interactive() -> bool:
    """Check if stdin is a TTY (interactive terminal)."""
    return sys.stdin.isatty()

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")

def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")

def get_project_root() -> Path:
    """Get the project root directory."""
    script_path = Path(__file__).resolve()
    # bin/ is in project root
    return script_path.parent.parent

def read_env_example(example_path: Path) -> Dict[str, str]:
    """Read .env.example file and return a dictionary of key-value pairs."""
    env_vars = {}
    if not example_path.exists():
        return env_vars
    
    with open(example_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE format
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def read_env_file(env_path: Path) -> Dict[str, str]:
    """Read existing .env file and return a dictionary of key-value pairs."""
    env_vars = {}
    if not env_path.exists():
        return env_vars
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE format
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def prompt_for_value(key: str, default: str, description: Optional[str] = None) -> str:
    """Prompt user for an environment variable value."""
    if not is_interactive():
        # Non-interactive mode: return default
        return default
    
    prompt = f"{Colors.BOLD}{key}{Colors.RESET}"
    if description:
        prompt += f" ({description})"
    if default and default != f"your_{key.lower()}" and not default.startswith("your_"):
        prompt += f" [{default}]"
    prompt += ": "
    
    try:
        value = input(prompt).strip()
        return value if value else default
    except (EOFError, KeyboardInterrupt):
        # Handle Ctrl+C or EOF gracefully
        print("\n")
        return default

def generate_env_file(
    example_path: Path,
    env_path: Path,
    env_name: str,
    interactive: bool = True,
    defaults: Optional[Dict[str, str]] = None,
    update: bool = False
) -> bool:
    """Generate or update .env file from .env.example."""
    defaults = defaults or {}
    
    if not example_path.exists():
        print_error(f".env.example not found at {example_path}")
        return False
    
    example_vars = read_env_example(example_path)
    if not example_vars:
        print_warning(f"No environment variables found in {example_path}")
        return False
    
    # Read existing .env file if it exists
    existing_vars = read_env_file(env_path) if env_path.exists() else {}
    file_exists = env_path.exists()
    
    if file_exists and not update:
        print_warning(f".env already exists at {env_path}")
        if interactive and is_interactive():
            try:
                response = input("Update from .env.example? (y/N): ").strip().lower()
                if response != 'y':
                    print_info(f"Skipping {env_name} .env generation")
                    return False
                update = True
            except (EOFError, KeyboardInterrupt):
                print("\n")
                print_info(f"Skipping {env_name} .env generation")
                return False
        else:
            # Non-interactive mode: update by default if file exists
            update = True
    
    action = "Updating" if (file_exists and update) else "Generating"
    print_info(f"{action} .env for {env_name}...")
    
    # Merge existing vars with example vars
    # Preserve existing values, add missing ones from example
    generated_vars = existing_vars.copy()
    missing_vars = []
    
    for key, default_value in example_vars.items():
        if key not in generated_vars:
            missing_vars.append(key)
            # Use provided defaults if available
            if key in defaults:
                generated_vars[key] = defaults[key]
            elif interactive and is_interactive():
                # Extract description from comment if available
                description = None
                with open(example_path, 'r') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if key in line and i > 0:
                            prev_line = lines[i-1].strip()
                            if prev_line.startswith('#'):
                                description = prev_line[1:].strip()
                            break
                
                value = prompt_for_value(key, default_value, description)
                generated_vars[key] = value
            else:
                # Non-interactive mode: use default from example
                generated_vars[key] = default_value
    
    if missing_vars and update:
        print_info(f"Added {len(missing_vars)} missing variable(s): {', '.join(missing_vars)}")
    
    # Add any variables that exist in .env but not in .env.example (preserve custom vars)
    custom_vars = {k: v for k, v in existing_vars.items() if k not in example_vars}
    
    # Write .env file preserving structure from example
    with open(env_path, 'w') as f:
        f.write(f"# Generated from {example_path.name}\n")
        f.write("# DO NOT commit this file to version control\n\n")
        
        # Write variables grouped by comments, preserving example structure
        with open(example_path, 'r') as example:
            in_section = False
            for line in example:
                stripped = line.strip()
                if stripped.startswith('#'):
                    f.write(line)
                    in_section = True
                elif stripped and '=' in stripped:
                    key = stripped.split('=', 1)[0].strip()
                    if key in generated_vars:
                        f.write(f"{key}={generated_vars[key]}\n")
                elif not stripped and in_section:
                    f.write("\n")
        
        # Add custom variables at the end if any exist
        if custom_vars:
            f.write("\n# Custom variables (not in .env.example)\n")
            for key, value in custom_vars.items():
                f.write(f"{key}={value}\n")
    
    if file_exists and update:
        print_success(f"Updated .env file at {env_path}")
    else:
        print_success(f"Generated .env file at {env_path}")
    return True

def main():
    """Main function."""
    project_root = get_project_root()

    # Parse command line arguments
    interactive = '--non-interactive' not in sys.argv
    skip_api = '--skip-api' in sys.argv
    skip_client = '--skip-client' in sys.argv
    update = '--update' in sys.argv or '--refresh' in sys.argv

    print(f"{Colors.BOLD}Environment Setup Script{Colors.RESET}\n")

    success_count = 0
    total_count = 0

    # Discover all .env.example files in the repository
    env_examples = sorted(
        project_root.rglob('.env.example'),
        key=lambda p: p.relative_to(project_root).parts,
    )

    for example_path in env_examples:
        relative_dir = example_path.parent.relative_to(project_root)
        env_name = str(relative_dir)

        # Maintain backward compatibility with legacy skip flags
        if env_name == "api" and skip_api:
            print_info("Skipping API .env generation (--skip-api)")
            continue
        if env_name == "client" and skip_client:
            print_info("Skipping Client .env generation (--skip-client)")
            continue

        total_count += 1
        env_path = example_path.with_name('.env')
        if generate_env_file(example_path, env_path, env_name, interactive, update=update):
            success_count += 1

    print(f"\n{Colors.BOLD}Setup complete!{Colors.RESET}")
    action = "Updated" if update else "Generated"
    print(f"{action} {success_count}/{total_count} .env file(s)")
    
    if success_count > 0:
        print_info("Remember to update the .env files with your actual values")
    
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())