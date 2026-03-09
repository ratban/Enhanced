import os
import subprocess
import shutil
import sys

def run_test():
    print("=== ENPM Ecosystem Test ===")
    
    # Paths
    project_dir = os.getcwd()
    test_dir = os.path.join(project_dir, "tests", "ecosystem_test_run")
    enhc_py = os.path.join(project_dir, "enhanced", "enhc.py")
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 1. Create app manifest
    manifest_content = """this is the "test_app" package.
the version is "1.0.0".
the author is "tester".
use the "math_lib" package version "1.0.0".
"""
    with open(os.path.join(test_dir, "manifest.en"), "w") as f:
        f.write(manifest_content)
        
    # 2. Create app code
    app_code = """use the "math_lib" package.

the number x is math_lib's add with 40 and 2.
say "Answer is: " then x.
"""
    main_en = os.path.join(test_dir, "main.en")
    with open(main_en, "w") as f:
        f.write(app_code)
        
    print("→ Running 'enhc get' in test directory...")
    # Change to test dir to run enhc
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    
    try:
        # Run enhc get
        subprocess.run([sys.executable, enhc_py, "get", "the", "math_lib", "package"], check=True)
        
        if os.path.exists("enhanced_packages/math_lib"):
            print("✓ Package math_lib fetched successfully.")
        else:
            print("✗ Package math_lib FETCH FAILED.")
            return False
            
        # 3. Run compilation
        print("→ Compiling main.en...")
        subprocess.run([sys.executable, enhc_py, "main.en", "--run"], check=True)
        print("✓ Compilation and execution successful!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    finally:
        os.chdir(original_cwd)
        
    return True

if __name__ == "__main__":
    if run_test():
        print("\n[PASSED]")
        sys.exit(0)
    else:
        print("\n[FAILED]")
        sys.exit(1)
