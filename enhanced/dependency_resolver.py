import os
import shutil

class DependencyResolver:
    def __init__(self, registry_path):
        self.registry_path = registry_path

    def resolve(self, project_root, manifest):
        """
        Takes a Manifest AST node and resolves dependencies by copying 
        them from Registry to project_root/enhanced_packages/.
        """
        packages_dir = os.path.join(project_root, "enhanced_packages")
        if not os.path.exists(packages_dir):
            os.makedirs(packages_dir)

        for dep in manifest.dependencies:
            pkg_name = dep.package_name
            version = dep.version
            source = dep.source # github URL etc, ignored for simulation

            print(f"→ Resolving dependency: {pkg_name} {version or ''}")
            
            src = os.path.join(self.registry_path, pkg_name)
            dst = os.path.join(packages_dir, pkg_name)

            if os.path.exists(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"  ✓ Installed {pkg_name} to enhanced_packages/")
            else:
                # Check if it exists locally as a root folder
                local_src = os.path.join(project_root, pkg_name)
                if os.path.exists(local_src) and os.path.isdir(local_src):
                     print(f"  ✓ Using local version of {pkg_name}")
                else:
                     print(f"  ⚠ Error: Package {pkg_name} not found in Registry.")
