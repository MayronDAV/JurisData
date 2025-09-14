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

class PyInstallerCompiler:
    def __init__(self):
        self.config = {
            'onefile': True,
            'noconsole': True,
            'icon': None,
            'name': None,
            'add_data': [],
            'hidden_imports': [],
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
        os.makedirs(resolved_build_dir, exist_ok=True)

        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--onefile' if self.config['onefile'] else '',
            '--noconsole' if self.config['noconsole'] else '--console',
            '--name', self.config['name'] or script_name,
            '--distpath', resolved_output_dir,
            '--workpath', resolved_build_dir,
            '--specpath', '.'
        ]
        
        # Resolve and add icon if specified
        if self.config['icon']:
            icon_exists, resolved_icon_path = self.path_exists(self.config['icon'], batch_file_dir)
            if icon_exists:
                cmd.extend(['--icon', resolved_icon_path])
            else:
                print(f"Warning: Icon file not found: {self.config['icon']}")
        
        # Add data files (resolve paths)
        for data in self.config['add_data']:
            if ';' in data:
                src, dest = data.split(';', 1)
                src_exists, resolved_src = self.path_exists(src, batch_file_dir)
                if src_exists:
                    cmd.extend(['--add-data', f"{resolved_src};{dest}"])
                else:
                    print(f"Warning: Data source not found: {src}")
            else:
                cmd.extend(['--add-data', data])
        
        # Add hidden imports
        for hidden_import in self.config['hidden_imports']:
            cmd.extend(['--hidden-import', hidden_import])
        
        # Remove empty arguments
        cmd = [arg for arg in cmd if arg]
        
        # Add the resolved script path
        cmd.append(resolved_script_path)
        
        print(f"Running: {' '.join(cmd)}")
        print(f"Working directory: {os.getcwd()}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                print(f"Compilation completed successfully!")
                executable_name = f"{self.config['name'] or script_name}.exe"
                executable_path = os.path.join(resolved_output_dir, executable_name)
                print(f"Executable: {executable_path}")
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
    parser.add_argument('--add-data', action='append', help='Additional data (e.g. "src;src")')
    parser.add_argument('--hidden-import', action='append', help='Hidden imports')
    parser.add_argument('--batch', help='JSON file with list of scripts to compile')
    parser.add_argument('--clean', action='store_true', help='Clean up build files after compilation')
    
    args = parser.parse_args()
    
    compiler = PyInstallerCompiler()
    
    config = {
        'onefile': args.onefile if args.onefile else compiler.config['onefile'],
        'noconsole': not args.console,
        'icon': args.icon,
        'name': args.name,
        'output_dir': args.output_dir,
        'add_data': args.add_data or [],
        'hidden_imports': args.hidden_import or [],
        'clean_build': args.clean
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