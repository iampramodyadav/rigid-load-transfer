# rigid-load-transfer
# Rigid Load Transfer Analysis Tool Documentation

![Demo](https://via.placeholder.com/800x400.png?text=3D+Visualization+Demo)  
*A web-based tool for analyzing load transfer between coordinate systems with 3D visualization*

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage Guide](#usage-guide)
5. [Input File Format](#input-file-format)
6. [Examples](#examples)
7. [Troubleshooting](#troubleshooting)
8. [License](#license)

---

## Overview <a name="overview"></a>
The **Rigid Load Transfer Analysis Tool** is a Dash-based web application that:
- Calculates load/moment transfers between coordinate systems
- Visualizes systems and force vectors in 3D space
- Supports multiple input systems and target systems
- Exports/imports configurations via JSON files

Designed for mechanical engineers and analysts working with coordinate system transformations.

---

## Features <a name="features"></a>
### Core Functionality
- 🖥️ Interactive 3D visualization with Plotly
- ➕ Add unlimited load/target systems
- 🔄 Real-time force/moment calculations
- 📊 Results displayed in sortable tables
- 🎨 Automatic color coding for systems

### Advanced Features
- 📁 JSON import/export of configurations
- 🔗 Connection lines between systems
- 🧭 Custom Euler angle rotation orders
- ✏️ Editable system names
- 🛑 Input validation and error handling

---

## Installation <a name="installation"></a>
### Requirements
- Python 3.8+
- pip package manager

### Steps
1. Clone repository:
   ```bash
   git clone https://github.com/iampramodyadav/rigid-load-transfer.git
   cd rigid-load-transfer
   ```

2. Install dependencies:
   ```bash
   pip install dash numpy plotly
   ```

3. Run application:
   ```bash
   python rlt.py
   ```

4. Access in browser: `http://localhost:8050`

---

## Usage Guide <a name="usage-guide"></a>
### Interface Overview
![UI Layout](https://via.placeholder.com/600x300.png?text=Interface+Layout)

1. **Input Panel (Left)**
   - Add/configure load/target systems
   - Import/export configurations
   - System naming and parameters

2. **Visualization Panel (Right)**
   - 3D coordinate system display
   - Force/moment vectors
   - Connection lines between systems
   - Results table

### Step-by-Step Workflow
1. **Add Systems**
   - Click `➕ Add Load System` for force inputs
   - Click `➕ Add Target System` for calculation targets

2. **Configure Systems**
   - Enter position (X,Y,Z) in meters
   - Set rotation angles (degrees) and order
   - Name systems for easy identification
   - Input forces/moments (N, N·m)

3. **Visualize Results**
   - Interactive 3D view with zoom/rotate
   - Hover over vectors for values
   - Results update automatically

4. **Save/Load Configurations**
   - Use `📁 Upload Input File` for JSON imports
   - Click `💾 Export Data` to save current state

---

## Input File Format <a name="input-file-format"></a>
### JSON Structure Example
```json
{
  "loads": [
    {
      "name": "Main Engine Load",
      "force": [1500, 0, 0],
      "moment": [0, 300, 0],
      "euler_angles": [30, 45, 60],
      "rotation_order": "zyx",
      "translation": [2.5, 1.0, 0.0],
      "color": {"hex": "#FF0000"}
    }
  ],
  "targets": [
    {
      "name": "Fuselage Interface",
      "euler_angles": [90, 0, 0],
      "rotation_order": "xyz",
      "translation": [5.0, 2.5, 1.0],
      "color": {"hex": "#00FF00"}
    }
  ]
}
```

### Field Descriptions
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Custom system identifier |
| `translation` | [float, float, float] | X,Y,Z position in meters |
| `rotation_order` | string | Euler rotation sequence (e.g., 'xyz') |
| `euler_angles` | [float, float, float] | Rotation angles in **degrees** |
| `force` | [float, float, float] | Force components (N) |
| `moment` | [float, float, float] | Moment components (N·m) |
| `color.hex` | string | System color in HEX format |

---

## Examples <a name="examples"></a>
### Simple Cantilever Beam
```json
{
  "loads": [{
    "name": "End Load",
    "force": [0, 0, -1000],
    "moment": [0, 0, 0],
    "euler_angles": [0, 0, 0],
    "rotation_order": "xyz",
    "translation": [5, 0, 0],
    "color": {"hex": "#FF0000"}
  }],
  "targets": [{
    "name": "Fixed Support",
    "euler_angles": [0, 0, 0],
    "rotation_order": "xyz",
    "translation": [0, 0, 0],
    "color": {"hex": "#00FF00"}
  }]
}
```

### Multi-system Configuration
![Multi-system](https://via.placeholder.com/600x300.png?text=Multi-System+Example)  
*Shows load transfer between engine mounts and airframe interfaces*

---

## Troubleshooting <a name="troubleshooting"></a>
### Common Issues
**Problem**: Input fields clear when empty  
**Solution**: Enter 0 instead of leaving fields blank

**Problem**: File upload errors  
**Solution**: Ensure JSON format matches specification

**Problem**: Vectors not visible  
**Solution**: Check force/moment magnitudes > 1N/N·m

**Problem**: Rotation order confusion  
**Solution**: Use right-hand rule with specified sequence

---

## License <a name="license"></a>
MIT License  
Copyright © 2024 Pramod Kumar Yadav

**Contact**: [pkyadav01234@gmail.com](mailto:pkyadav01234@gmail.com)

---

*Documentation generated using [Markdown Guide](https://www.markdownguide.org/)*  
*Tool version: 1.2.0 | Last updated: 2024-02-15*
