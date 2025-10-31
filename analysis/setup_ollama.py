#!/usr/bin/env python3
"""
Setup Ollama with custom model path for GeoGPT
Models will be stored in the project directory
"""

import os
import sys
import subprocess
import time
import requests
import json
from pathlib import Path

class OllamaSetup:
    def __init__(self, project_path=None):
        # Set project path
        if project_path is None:
            self.project_path = Path(__file__).parent.absolute()
        else:
            self.project_path = Path(project_path)
        
        # Set custom model path
        self.model_path = self.project_path / "ollama_models"
        self.config_file = self.project_path / "ollama_config.env"
        self.log_file = self.project_path / "ollama.log"
        
    def create_directories(self):
        """Create necessary directories"""
        print(f"📁 Project Path: {self.project_path}")
        print(f"📁 Model Path: {self.model_path}")
        
        if not self.model_path.exists():
            print("\n📁 Creating model directory...")
            self.model_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Directory created: {self.model_path}")
        else:
            print("\n✅ Model directory already exists")
    
    def check_ollama_installed(self):
        """Check if Ollama is installed"""
        try:
            subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                check=True
            )
            print("✅ Ollama is installed")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Ollama not found!")
            print("📦 Please install from: https://ollama.com/download")
            return False
    
    def stop_existing_service(self):
        """Stop any running Ollama service"""
        print("\n🛑 Stopping existing Ollama service...")
        try:
            if sys.platform == 'win32':
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'ollama.exe'],
                    capture_output=True
                )
            else:
                subprocess.run(['pkill', '-9', 'ollama'], capture_output=True)
            time.sleep(2)
            print("✅ Stopped existing service")
        except:
            print("ℹ  No existing service to stop")
    
    def create_config(self):
        """Create configuration file"""
        print("\n🔧 Creating configuration...")
        
        config_content = f"""# Ollama Configuration for GeoGPT
OLLAMA_MODELS={self.model_path}
OLLAMA_HOST=127.0.0.1:11434
"""
        
        with open(self.config_file, 'w') as f:
            f.write(config_content)
        
        print(f"✅ Configuration saved to: {self.config_file}")
        print(f"   Models will be stored in: {self.model_path}")
    
    def set_environment(self):
        """Set environment variables"""
        os.environ['OLLAMA_MODELS'] = str(self.model_path)
        os.environ['OLLAMA_HOST'] = '127.0.0.1:11434'
    
    def start_service(self):
        """Start Ollama service with custom path"""
        print("\n🚀 Starting Ollama service with custom model path...")
        
        self.set_environment()
        
        try:
            # Start Ollama in background
            log_handle = open(self.log_file, 'w')
            
            if sys.platform == 'win32':
                # Windows
                process = subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Linux/Mac
                process = subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT
                )
            
            print(f"✅ Ollama service started (PID: {process.pid})")
            print(f"   Log file: {self.log_file}")
            
            # Wait for service to be ready
            print("   Waiting for service to be ready...")
            for i in range(10):
                time.sleep(1)
                if self.check_service_health():
                    print("✅ Service is ready!")
                    return True
            
            print("⚠  Service started but not responding yet")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start service: {e}")
            return False
    
    def check_service_health(self):
        """Check if Ollama service is running"""
        try:
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def list_models(self):
        """List currently installed models"""
        print("\n📋 Currently installed models:")
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                env=os.environ
            )
            print(result.stdout)
            return result.stdout
        except Exception as e:
            print(f"❌ Failed to list models: {e}")
            return ""
    
    def pull_model(self, model_name):
        """Download a model"""
        print(f"\n📥 Downloading {model_name} to {self.model_path}...")
        print("   (This may take several minutes depending on model size)")
        print()
        
        try:
            process = subprocess.Popen(
                ['ollama', 'pull', model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ
            )
            
            # Stream output
            for line in process.stdout:
                print(line, end='', flush=True)
            
            process.wait()
            
            if process.returncode == 0:
                print("\n✅ Model downloaded successfully!")
                return True
            else:
                print(f"\n❌ Failed to download model (exit code: {process.returncode})")
                return False
                
        except Exception as e:
            print(f"\n❌ Error downloading model: {e}")
            return False
    
    def test_model(self, model_name):
        """Test the model"""
        print("\n🧪 Testing model...")
        
        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    "model": model_name,
                    "prompt": "Say 'Hello from Llama!' in 5 words or less.",
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                print("✅ Model is working!")
                print(f"   Response: {response_text.strip()}")
                return True
            else:
                print(f"⚠  Model test returned status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠  Model test failed: {e}")
            return False
    
    def create_startup_script(self):
        """Create a script to easily restart Ollama"""
        if sys.platform == 'win32':
            startup_file = self.project_path / "start_ollama.bat"
            content = f"""@echo off
REM Start Ollama with custom model path for GeoGPT
echo 🚀 Starting Ollama for GeoGPT...
echo 📁 Models directory: {self.model_path}
set OLLAMA_MODELS={self.model_path}
set OLLAMA_HOST=127.0.0.1:11434
start /B ollama serve > "{self.log_file}" 2>&1
echo ✅ Ollama started
echo 📊 Check status: curl http://localhost:11434/api/tags
pause
"""
        else:
            startup_file = self.project_path / "start_ollama.sh"
            content = f"""#!/bin/bash
# Start Ollama with custom model path for GeoGPT
echo "🚀 Starting Ollama for GeoGPT..."
echo "📁 Models directory: {self.model_path}"
export OLLAMA_MODELS="{self.model_path}"
export OLLAMA_HOST="127.0.0.1:11434"
ollama serve > "{self.log_file}" 2>&1 &
echo "✅ Ollama started (PID: $!)"
echo "📊 Check status: curl http://localhost:11434/api/tags"
"""
        
        with open(startup_file, 'w') as f:
            f.write(content)
        
        if sys.platform != 'win32':
            os.chmod(startup_file, 0o755)
        
        print(f"\n📝 Startup script created: {startup_file}")
        return startup_file
    
    def show_summary(self, model_name, startup_file):
        """Show setup summary"""
        print("\n" + "=" * 60)
        print("✅ Setup Complete!")
        print("=" * 60)
        print(f"\n📂 Model Location: {self.model_path}")
        print(f"🦙 Model Installed: {model_name}")
        print(f"\n📝 Configuration:")
        print(f"   - Config file: {self.config_file}")
        print(f"   - Startup script: {startup_file}")
        print(f"   - Log file: {self.log_file}")
        print(f"\n🔄 To restart Ollama with this configuration:")
        if sys.platform == 'win32':
            print(f"   {startup_file}")
        else:
            print(f"   bash {startup_file}")
        print(f"\n💡 To use in Python, add this to your code:")
        print(f"   import os")
        print(f"   os.environ['OLLAMA_MODELS'] = r'{self.model_path}'")
        print(f"\nNext steps:")
        print("1. Test LLM: python llm_interface.py")
        print("2. Start API: python analysis_api_with_llm.py")
        print("3. Test API: python test_llm_api.py")
        print(f"\n🦙 Llama is ready for GeoGPT!")

def main():
    print("🦙 Setting up Llama for GeoGPT")
    print("=" * 60)
    
    # Initialize setup
    project_path = r"C:\Users\sanji\OneDrive\Desktop\Sanji\.vscode\Digital_Twin\Satellite-Digital-Twin\analysis"
    setup = OllamaSetup(project_path)
    
    # Create directories
    setup.create_directories()
    
    # Check Ollama installation
    if not setup.check_ollama_installed():
        sys.exit(1)
    
    # Stop existing service
    setup.stop_existing_service()
    
    # Create config
    setup.create_config()
    
    # Start service
    if not setup.start_service():
        print("\n⚠  Service may not be fully ready. Please wait and try again.")
        sys.exit(1)
    
    # List existing models
    setup.list_models()
    
    # Choose model
    print("\n📥 Choose a model to download:")
    print("   1. llama3.2:1b  (~1.3GB) - Smallest, fastest")
    print("   2. llama3.2:3b  (~2GB)   - Recommended balance")
    print("   3. llama3.2     (~2GB)   - Standard")
    print("   4. llama3.1:8b  (~4.7GB) - Best quality")
    
    choice = input("\nEnter choice [1-4, default: 2]: ").strip() or "2"
    
    models = {
        '1': 'llama3.2:1b',
        '2': 'llama3.2:3b',
        '3': 'llama3.2',
        '4': 'llama3.1:8b'
    }
    
    model_name = models.get(choice, 'llama3.2:3b')
    
    # Download model
    if not setup.pull_model(model_name):
        print("\n❌ Setup failed")
        sys.exit(1)
    
    # Verify
    setup.list_models()
    
    # Test model
    setup.test_model(model_name)
    
    # Create startup script
    startup_file = setup.create_startup_script()
    
    # Show summary
    setup.show_summary(model_name, startup_file)

if __name__ == "__main__":
    main()