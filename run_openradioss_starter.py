import subprocess
import os

# Set environment
env = os.environ.copy()
or_base_dir = "/home/nemo/Dokumente/Software/OpenRadioss_linux64"
env.update({
    'OPENRADIOSS_PATH': or_base_dir,
    'RAD_CFG_PATH': f"{or_base_dir}/OpenRadioss/hm_cfg_files",
    'RAD_H3D_PATH': f"{or_base_dir}/OpenRadioss/extlib/h3d/lib/linux64",
    'LD_LIBRARY_PATH': f"{or_base_dir}/OpenRadioss/extlib/hm_reader/linux64:{or_base_dir}/OpenRadioss/extlib/h3d/lib/linux64:{env.get('LD_LIBRARY_PATH', '')}"
})

# Test starter
starter_result = subprocess.run([
    f"{or_base_dir}/OpenRadioss/exec/starter_linux64_gf",
    "-i", "zug_test3_RS.k"
], cwd="/home/nemo/Dokumente/Sandbox/Fem_upgraded", 
   capture_output=True, text=True, env=env)

print(f"Starter exit code: {starter_result.returncode}")
print(f"Starter output: {starter_result.stdout}")

# Check if .rad file was created
rad_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/zug_test3_RS_0001.rad"
if os.path.exists(rad_file):
    print(f"✓ .rad file created: {rad_file}")
    
    # Test engine
    engine_result = subprocess.run([
        f"{or_base_dir}/OpenRadioss/exec/engine_linux64_gf_ompi",
        "-i", os.path.basename(rad_file)
    ], cwd="/home/nemo/Dokumente/Sandbox/Fem_upgraded",
       capture_output=True, text=True, env=env, timeout=10)
    
    print(f"Engine exit code: {engine_result.returncode}")
    print(f"Engine output: {engine_result.stdout[:500]}...")