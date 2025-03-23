"""
@Author:    Pramod Kumar Yadav
@email:     pkyadav01234@gmail.com
@Date:      Feb, 2025
@status:    development
@PythonVersion: python3

"""
import numpy as np

def create_rotation_matrix(euler_angles, rotation_order, translation):
    R = np.eye(3)
    for axis in reversed(rotation_order.lower()):
        idx = rotation_order.lower().index(axis)
        angle = euler_angles[idx]
        R = R @ _axis_rotation(axis, angle)
    return R, np.array(translation)

def _axis_rotation(axis, angle):
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)
    if axis == 'x':
        return np.array([[1, 0, 0], [0, cos_a, -sin_a], [0, sin_a, cos_a]])
    elif axis == 'y':
        return np.array([[cos_a, 0, sin_a], [0, 1, 0], [-sin_a, 0, cos_a]])
    elif axis == 'z':
        return np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])
    raise ValueError(f"Invalid axis: {axis}")

def rigid_load_transfer(force_local_A, moment_local_A, R_A, point_A_global, R_B, point_B_global):
    force_global = R_A @ force_local_A
    moment_global = R_A @ moment_local_A
    r = point_A_global - point_B_global
    moment_global += np.cross(r, force_global)
    return R_B.T @ force_global, R_B.T @ moment_global

# Example usage
if __name__ == "__main__":
    # Define coordinate system parameters
    euler_angles = [np.pi/2, 0, 0]  # 90° rotation about X
    rotation_order = "xyz"
    translation = [2, 3, 5]

    # Create rotation matrix and get translation
    R, t = create_rotation_matrix(euler_angles, rotation_order, translation)

    print("Rotation Matrix:")
    print(R)
    print("\nTranslation:", t)



def combine_loads(loads, target_system, include_gravity=True, gravity_data=None):
    """
    Combines multiple loads from different coordinate systems into a target system

    Parameters:
        loads: List of dictionaries containing:
            'force' - local force vector [x, y, z]
            'moment' - local moment vector [x, y, z]
            'euler_angles' - [rx, ry, rz] in radians
            'rotation_order' - e.g., 'xyz'
            'translation' - [x, y, z] in global system
            'mass' - mass in kg (optional)
            'cog' - center of gravity in local coordinates (optional)

        target_system: Dictionary containing:
            'euler_angles' - target system orientation
            'rotation_order' - target rotation order
            'translation' - target system position

        include_gravity: Boolean to include gravity effects
        
        gravity_data: Dictionary containing:
            'value' - gravity value in m/s²
            'direction' - gravity direction vector [x, y, z]

    Returns:
        total_force: Combined force in target system
        total_moment: Combined moment in target system
    """
    # Create target system rotation matrix
    R_target, target_pos = create_rotation_matrix(
        target_system['euler_angles'],
        target_system['rotation_order'],
        target_system['translation']
    )

    total_force = np.zeros(3)
    total_moment = np.zeros(3)

    # Set default gravity data if not provided
    if gravity_data is None:
        gravity_data = {'value': 9.81, 'direction': [0, 0, -1]}
    
    # Normalize gravity direction
    gravity_dir = np.array(gravity_data.get('direction', [0, 0, -1]))
    gravity_norm = np.linalg.norm(gravity_dir)
    if gravity_norm > 0:
        gravity_dir = gravity_dir / gravity_norm
    gravity_value = gravity_data.get('value', 9.81)

    for load in loads:
        # Create source system rotation matrix
        R_source, source_pos = create_rotation_matrix(
            load['euler_angles'],
            load['rotation_order'],
            load['translation']
        )

        # Get force and moment, defaulting to zeros if not present
        force = np.array(load.get('force', [0, 0, 0]))
        moment = np.array(load.get('moment', [0, 0, 0]))
        
        # Calculate gravity force if mass is present and gravity is enabled
        if include_gravity and 'mass' in load and load['mass'] > 0:
            mass = float(load['mass'])
            
            # Get center of gravity or use load position if not specified
            cog_local = np.array(load.get('cog', [0, 0, 0]))
            
            # Calculate gravity force in global coordinates
            gravity_force_global = mass * gravity_value * gravity_dir
            
            # Transform gravity force to local load coordinate system
            gravity_force_local = R_source.T @ gravity_force_global
            
            # Add gravity force to load force
            force = force + gravity_force_local
            
            # Calculate gravity moment (only if COG is not at origin)
            if not np.all(cog_local == 0):
                gravity_moment_local = np.cross(cog_local, R_source.T @ gravity_force_global)
                moment = moment + gravity_moment_local

        # Transfer load to target system
        F_trans, M_trans = rigid_load_transfer(
            force_local_A=force,
            moment_local_A=moment,
            R_A=R_source,
            point_A_global=source_pos,
            R_B=R_target,
            point_B_global=target_pos
        )

        # Accumulate results
        total_force += F_trans
        total_moment += M_trans

    return total_force, total_moment

# Example usage
if __name__ == "__main__":
    # Define target system (lc0)
    target_system = {
        'euler_angles': [np.pi/4, 0, 0],  # 45° about X
        'rotation_order': 'xyz',
        'translation': [2, 3, 1]
    }

    # Define three different load systems
    loads = [
        {   # Load System 1
            'force': [10, 0, 0],
            'moment': [0, 2, 0],
            'euler_angles': [0, 0, 0],
            'rotation_order': 'xyz',
            'translation': [0, 0, 0]
        },
        {   # Load System 2 (rotated 90° about Z)
            'force': [0, 5, 0],
            'moment': [0, 0, 3],
            'euler_angles': [0, 0, np.pi/2],
            'rotation_order': 'xyz',
            'translation': [1, 2, 0]
        },
        {   # Load System 3 (rotated 30° about Y)
            'force': [0, 0, 8],
            'moment': [1, 0, 0],
            'euler_angles': [0, np.pi/6, 0],
            'rotation_order': 'xyz',
            'translation': [0, 0, 3]
        }
    ]

    # Calculate combined load in target system
    total_F, total_M = combine_loads(loads, target_system)

    print("Combined Force in Target System:", np.round(total_F, 3))
    print("Combined Moment in Target System:", np.round(total_M, 3))