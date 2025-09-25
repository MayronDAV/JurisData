#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto Compiler Script - Compiles Python scripts into executables with PyInstaller
Usage: python compiler.py [script.py] [options]
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path

try:
    from PyInstaller.utils.hooks import collect_submodules, copy_metadata
except ImportError:
    collect_submodules = None
    copy_metadata = None


class PyInstallerCompiler:
    def __init__(self):
        self.config = {
            'onefile': True,
            'noconsole': True,
            'icon': None,
            'name': None,
            'add_data': [],
            'hidden_imports': [],
            'collect_submodules': [],
            'collect_metadata': [],
            'exclude_modules': [],
            'output_dir': 'dist',
            'build_dir': 'build',
            'clean_build': True
        }
    
    def check_pyinstaller(self):
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'show', 'PyInstaller'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def install_pyinstaller(self):
        print("Installing PyInstaller...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'PyInstaller'], 
                         check=True)
            print("PyInstaller installed successfully!")
            return True
        except subprocess.CalledProcessError:
            print("Failed to install PyInstaller. Please install it manually.")
            return False
    
    def resolve_path(self, path, base_dir=None):
        """Resolve relative paths to absolute paths"""
        if not path:
            return path
            
        if os.path.isabs(path):
            return path
            
        # If base_dir is provided, resolve relative to that directory
        if base_dir:
            return os.path.join(base_dir, path)
        
        # Otherwise, resolve relative to current working directory
        return os.path.abspath(path)
    
    def path_exists(self, path, base_dir=None):
        """Check if path exists, handling relative paths"""
        resolved_path = self.resolve_path(path, base_dir)
        return os.path.exists(resolved_path), resolved_path

    def generate_spec_file(self, script_path, config, batch_file_dir):
        """Generate a complete .spec file for PyInstaller with all configurations"""
        script_name = Path(script_path).stem
        exe_name = config.get('name') or script_name
        
        # Process hidden imports including collect_submodules
        all_hidden_imports = config.get('hidden_imports', [])[:]  # Copy the list
        
        # Add submodules from collect_submodules
        if collect_submodules:
            for mod in config.get('collect_submodules', []):
                try:
                    submodules = collect_submodules(mod)
                    all_hidden_imports.extend(submodules)
                    print(f"Added {len(submodules)} submodules from {mod}")
                except Exception as e:
                    print(f"Warning: could not collect submodules for {mod}: {e}")
        
        # Process datas including collect_metadata and add_data
        all_datas = self.format_datas(config.get('add_data', []), batch_file_dir)
        
        # Add metadata from collect_metadata
        if copy_metadata:
            for mod in config.get('collect_metadata', []):
                try:
                    metadata_files = copy_metadata(mod)
                    all_datas.extend(metadata_files)
                    print(f"Added metadata for {mod}: {metadata_files}")
                except Exception as e:
                    print(f"Warning: could not collect metadata for {mod}: {e}")
        
        # Process icon
        icon_section = ""
        if config.get('icon'):
            icon_exists, resolved_icon = self.path_exists(config['icon'], batch_file_dir)
            if icon_exists:
                icon_section = f"    icon='{resolved_icon}',"
        
        # Console setting
        console_setting = "True" if not config.get('noconsole', True) else "False"
        
        # Generate the spec file content with proper paths
        spec_template = f"""# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Add custom paths if needed
sys.path.insert(0, r'{os.path.dirname(script_path)}')

block_cipher = None

a = Analysis(
    [r'{script_path}'],
    pathex=[r'{os.path.dirname(script_path)}'],
    binaries=[],
    datas={all_datas},
    hiddenimports={all_hidden_imports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={config.get('exclude_modules', [])},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)"""

        # Add onefile or onedir section
        if config.get('onefile', True):
            spec_template += f"""
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{exe_name}',
{icon_section}
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={console_setting},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)"""
        else:
            spec_template += f"""
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{exe_name}',
{icon_section}
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={console_setting},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{exe_name}',
)"""
        
        return spec_template
    
    def format_datas(self, datas, batch_file_dir):
        """Format data files for .spec file"""
        formatted = []
        for data in datas:
            if ';' in data:
                src, dest = data.split(';', 1)
                src_exists, resolved_src = self.path_exists(src, batch_file_dir)
                if src_exists:
                    # Use raw string for paths to avoid escape issues
                    formatted.append((fr"{resolved_src}", dest))
            else:
                # Handle simple data entries
                formatted.append(data)
        return formatted

    def compile_script(self, script_path, config=None, batch_file_dir=None):
        if config:
            self.config.update(config)
        
        # Resolve script path
        script_exists, resolved_script_path = self.path_exists(script_path, batch_file_dir)
        if not script_exists:
            print(f"File not found: {script_path}")
            print(f"Resolved path: {resolved_script_path}")
            return False
        
        if not self.check_pyinstaller():
            if not self.install_pyinstaller():
                return False
        
        script_name = Path(resolved_script_path).stem
        print(f"Compiling {resolved_script_path}...")

        # Resolve output directories
        resolved_output_dir = self.resolve_path(self.config['output_dir'], batch_file_dir)
        resolved_build_dir = self.resolve_path(self.config['build_dir'], batch_file_dir)
        
        # Create output directories if they don't exist
        os.makedirs(resolved_output_dir, exist_ok=True)

        # Generate a .spec file with all configurations
        spec_content = self.generate_spec_file(resolved_script_path, self.config, batch_file_dir)
        
        spec_filename = f"{self.config['name'] or script_name}.spec"
        spec_path = os.path.join(os.path.dirname(resolved_script_path), spec_filename)
        
        # Write the spec file
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"Generated spec file: {spec_path}")
    
        cmd = [
            sys.executable, 
            "-m", 
            "PyInstaller",
            "--distpath", resolved_output_dir,
            "--workpath", resolved_build_dir,
            spec_path
        ]
        
        # Add clean option if specified
        if self.config.get('clean_build', True):
            cmd.append("--clean")
        
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                print(f"Compilation completed successfully!")
                executable_name = f"{self.config['name'] or script_name}.exe"
                executable_path = os.path.join(resolved_output_dir, executable_name)
                print(f"Executable: {executable_path}")
                
                # Clean up spec file if configured
                if self.config.get('clean_build', True):
                    try:
                        os.remove(spec_path)
                        print(f"Removed spec file: {spec_path}")
                    except Exception as e:
                        print(f"Warning: Could not remove spec file: {e}")
                
                return True
            else:
                print(f"Compilation error: {result.stderr}")
                if result.stdout:
                    print(f"Stdout: {result.stdout}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"Error running PyInstaller: {e}")
            print(f"Error output: {e.stderr}")
            if e.stdout:
                print(f"Stdout: {e.stdout}")
            
            # Don't remove spec file on error for debugging
            print(f"Spec file preserved for debugging: {spec_path}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
        
    def clean_build_files(self, batch_file_dir=None):
        try:
            resolved_build_dir = self.resolve_path(self.config['build_dir'], batch_file_dir)
            if os.path.exists(resolved_build_dir):
                import shutil
                shutil.rmtree(resolved_build_dir)
                print(f"Cleaned build directory: {resolved_build_dir}")
            
            # Remove .spec files from current directory
            for spec_file in Path('.').glob('*.spec'):
                spec_file.unlink()
                print(f"Removed spec file: {spec_file}")
                
        except Exception as e:
            print(f"Error cleaning files: {e}")
    
    def batch_compile(self, scripts_list, config=None, batch_file_path=None):
        results = {}
        batch_file_dir = os.path.dirname(batch_file_path) if batch_file_path else None
        
        for script in scripts_list:
            print(f"\n{'='*50}")
            print(f"Processing: {script}")
            print(f"{'='*50}")
            results[script] = self.compile_script(script, config, batch_file_dir)
        return results

def main():
    parser = argparse.ArgumentParser(description='Automatic Python script compiler using PyInstaller')
    parser.add_argument('script', nargs='?', help='Python script to compile')
    parser.add_argument('--onefile', action='store_true', help='Create single executable')
    parser.add_argument('--console', action='store_true', help='Keep console (overrides --noconsole)')
    parser.add_argument('--icon', help='Path to .ico icon file')
    parser.add_argument('--name', help='Custom executable name')
    parser.add_argument('--output-dir', default='dist', help='Output directory')
    parser.add_argument('--workpath', default='build', help='Build working directory')
    parser.add_argument('--add-data', action='append', help='Additional data (e.g. "src;src")')
    parser.add_argument('--hidden-import', action='append', help='Hidden imports')
    parser.add_argument('--collect-submodules', action='append', help='Collect all submodules of a package')
    parser.add_argument('--collect-metadata', action='append', help='Collect package metadata')
    parser.add_argument('--exclude-module', action='append', help='Exclude module from build')
    parser.add_argument('--batch', help='JSON file with list of scripts to compile')
    parser.add_argument('--clean', action='store_true', help='Clean up build files after compilation')
    parser.add_argument('--no-clean', action='store_true', help='Keep build files after compilation')
    
    args = parser.parse_args()
    
    compiler = PyInstallerCompiler()
    
    config = {
        'onefile': args.onefile if args.onefile else compiler.config['onefile'],
        'noconsole': not args.console,
        'icon': args.icon,
        'name': args.name,
        'output_dir': args.output_dir,
        'build_dir': args.workpath,
        'add_data': args.add_data or [],
        'hidden_imports': args.hidden_import or [],
        'collect_submodules': args.collect_submodules or [],
        'collect_metadata': args.collect_metadata or [],
        'exclude_modules': args.exclude_module or [],
        'clean_build': not args.no_clean  # Invert logic for clarity
    }
    
    if args.batch:
        try:
            batch_file_path = os.path.abspath(args.batch)
            batch_file_dir = os.path.dirname(batch_file_path)
            
            print(f"Loading batch config from: {batch_file_path}")
            print(f"Batch file directory: {batch_file_dir}")
            
            with open(batch_file_path, 'r', encoding='utf-8') as f:
                batch_config = json.load(f)
            
            scripts = batch_config.get('scripts', [])
            batch_config_settings = batch_config.get('config', {})
            
            if scripts:
                # Update config with batch settings
                config.update(batch_config_settings)
                
                # Change to batch file directory to handle relative paths correctly
                original_cwd = os.getcwd()
                try:
                    os.chdir(batch_file_dir)
                    print(f"Changed working directory to: {batch_file_dir}")
                    
                    results = compiler.batch_compile(scripts, config, batch_file_path)
                    print(f"\nResults: {sum(results.values())}/{len(results)} successful compilations")
                    
                finally:
                    os.chdir(original_cwd)
                    print(f"Restored working directory to: {original_cwd}")
            else:
                print("No scripts found in batch file")
                
        except FileNotFoundError:
            print(f"Batch file not found: {args.batch}")
        except json.JSONDecodeError as e:
            print(f"Error reading JSON file {args.batch}: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    
    elif args.script:
        success = compiler.compile_script(args.script, config)
        if success and config['clean_build']:
            compiler.clean_build_files()
    
    else:
        print("Automatic PyInstaller Compiler")
        print("=" * 40)
        
        script_path = input("Python script path: ").strip().strip('"')
        
        if script_path and os.path.exists(script_path):
            custom_name = input("Custom Name (Enter for default): ").strip() or None
            icon_path = input(".ico icon path (Enter to skip): ").strip() or None
            
            if icon_path and not os.path.exists(icon_path):
                print("Icon not found, still no icon will be used.")
                icon_path = None
            
            config.update({
                'name': custom_name,
                'icon': icon_path
            })
            
            success = compiler.compile_script(script_path, config)
            if success and config['clean_build']:
                compiler.clean_build_files()
        else:
            print("Script not found or not specified")

if __name__ == "__main__":
    main()