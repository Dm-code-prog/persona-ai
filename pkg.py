import os
import pkg_resources

packages = {d.project_name: d.location for d in pkg_resources.working_set}
sizes = {}

for pkg, location in packages.items():
    try:
        size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, filenames in os.walk(os.path.join(location, pkg)) for f in filenames)
        sizes[pkg] = size / (1024 * 1024)  # Convert bytes to MB
    except Exception:
        continue

sorted_sizes = sorted(sizes.items(), key=lambda x: x[1], reverse=True)

print("\nLargest packages:")
for name, size in sorted_sizes[:100]:  # Show top 20
    print(f"{name}: {size:.2f} MB")