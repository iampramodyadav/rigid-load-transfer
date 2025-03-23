"""
@Author:    Pramod Kumar Yadav
@email:     pkyadav01234@gmail.com
@Date:      Feb, 2023
@status:    development
@PythonVersion: python3

"""
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, ALL
import plotly.graph_objects as go
import numpy as np
import json
import base64
import io
import os
import re
# import dash_daq as daq
import plot_3d as plot3d
import rigid_load_transfer as rlt

# ---------------------------------------- THEMES ----------------------------------------
PLOT_THEMES = {
    'default': {
        'bg_color': 'white',
        'grid_color': '#E5ECF6',
        'axis_color': 'black',
        'text_color': 'black'
    },
    'dark': {
        'bg_color': '#283442',
        'grid_color': '#3B4754',
        'axis_color': '#EBF0F8',
        'text_color': '#EBF0F8'
    },
    'minimal': {
        'bg_color': 'white',
        'grid_color': '#F5F5F5',
        'axis_color': '#666666',
        'text_color': '#666666'
    },
    'night': {
        'bg_color': '#1a1a1a',
        'grid_color': '#333333',
        'axis_color': '#999999',
        'text_color': '#cccccc'
    },
    'blueprint': {
        'bg_color': '#F0F8FF',
        'grid_color': '#B0C4DE',
        'axis_color': '#4682B4',
        'text_color': '#4682B4'
    }
}
# --------------------------------- Initialize Dash app ----------------------------------
# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server
# ---------------------------------------- layout ----------------------------------------
app.layout = html.Div([
    # html.Div([    
    html.H1("Rigid Load Transfer Tool", style={
        'textAlign': 'center', 
        'color': '#2c3e50', 
        'fontFamily': 'Arial', 
        'marginBottom': '10px'
    }),
    
    dcc.Store(id='loads-store', data=[]),
    dcc.Store(id='targets-store', data=[]),
    dcc.Store(id='gravity-store', data={'value': 9.81, 'direction': [0, 0, -1]}),
    dcc.Download(id="download-data"), 
    html.Div([
        html.Div([
            # html.H3("Input Systems", style={'color': '#2980b9'}),
            
            dcc.Upload(id='upload-data',
                children=html.Button('📁 Upload Input File', style={
                    'width': '100%', 
                    'backgroundColor': '#3498db', 
                    'color': 'white',
                    'border': 'none',
                    'padding': '10px',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'fontSize': '16px',
                    'marginBottom': '10px'
                }),multiple=False,),
            
            # Gravity settings
            html.Div([
                html.H4("Gravity Settings", style={'marginBottom': '5px'}),
                html.Div([
                    html.Label("Gravity Value (m/s²):"),
                    dcc.Input(id='gravity-value', type='number', value=9.81, style={'width': '80px'})
                ], style={'marginBottom': '5px'}),
                html.Div([
                    html.Label("Gravity Direction (X,Y,Z):"),
                    dcc.Input(id='gravity-x', type='number', value=0, style={'width': '50px'}),
                    dcc.Input(id='gravity-y', type='number', value=0, style={'width': '50px'}),
                    dcc.Input(id='gravity-z', type='number', value=-1, style={'width': '50px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '5px', 'marginBottom': '10px'})
            ], style={'padding': '10px', 'backgroundColor': '#f5f5f5', 'borderRadius': '5px', 'marginBottom': '10px'}),
                       
            html.Button('➕ Add Load System', id='add-load-btn', n_clicks=0, style={
                'width': '100%', 
                'backgroundColor': '#27ae60', 
                'color': 'white',
                'border': 'none',
                'padding': '10px',
                'borderRadius': '5px',
                'cursor': 'pointer',
                'fontSize': '16px'
            }),
            html.Div(id='load-inputs-container', style={'marginTop': '10px'}),
            html.Hr(style={'border': '1px solid #ccc'}),

            html.Button('➕ Add Target System', id='add-target-btn', n_clicks=0, style={
                'width': '100%', 
                'backgroundColor': '#e67e22', 
                'color': 'white',
                'border': 'none',
                'padding': '10px',
                'borderRadius': '5px',
                'cursor': 'pointer',
                'fontSize': '16px'
            }),
            html.Div(id='target-inputs-container', style={'marginTop': '10px'}),
            
            # Add the export button to your layout (in the input systems section)
            html.Div([
                html.Hr(style={'border': '1px solid #ccc', 'marginTop': '10px'}),
                html.Div([
                    dcc.RadioItems(
                        id='export-format',
                        options=[
                            {'label': 'Classic Format (loads/targets)', 'value': 'classic'},
                            {'label': 'New Format (nodes/edges)', 'value': 'new'},
                            {'label': 'Auto Detect', 'value': 'auto'}
                        ],
                        value='auto',
                        labelStyle={'display': 'block', 'marginBottom': '5px'},
                        style={'marginBottom': '10px'}
                    ),
                ], style={'marginBottom': '10px'}),
                html.Button('💾 Export Data', id='export-btn', style={
                    'width': '100%', 
                    'backgroundColor': '#3498db', 
                    'color': 'white',
                    'border': 'none',
                    'padding': '10px',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'fontSize': '16px'
                }),
            ], style={'marginTop': '10px'}),
         #--------------------------- Simplified theme selector using Plotly templates --------------------------
            # html.Div([
            #     html.Label("Select Theme:", style={'marginRight': '10px'}),
            #     dcc.Dropdown(
            #         id='theme-selector',
            #         options=[
            #             {'label': 'Plotly', 'value': 'plotly'},
            #             {'label': 'Plotly White', 'value': 'plotly_white'},
            #             {'label': 'Plotly Dark', 'value': 'plotly_dark'},
            #             {'label': 'ggplot2', 'value': 'ggplot2'},
            #             {'label': 'Seaborn', 'value': 'seaborn'},
            #             {'label': 'Simple White', 'value': 'simple_white'},
            #             {'label': 'None', 'value': 'none'}
            #         ],
            #         value='plotly',
            #         style={'width': '200px', 'alignItems': 'left',}
            #     ),
            # ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'})

        # -------------------- Add theme selector --------------------
            html.Div([
                html.Label("Plot Theme:", style={'marginRight': '10px'}),
                dcc.Dropdown(
                    id='theme-selector',
                    options=[
                        {'label': 'Default', 'value': 'default'},
                        {'label': 'Dark', 'value': 'dark'},
                        {'label': 'Minimal', 'value': 'minimal'},
                        {'label': 'Night', 'value': 'night'},
                        {'label': 'Blueprint', 'value': 'blueprint'}
                    ], value='default', style={'width': '200px'}
                )
            ], style={'display': 'flex','alignItems': 'center','justifyContent': 'flex-end','padding': '10px 20px'
            }),
        #---------------------------------------------------------------------------------------------------
        ], style={
            'width': '25%', 
            'padding': '15px',
            'borderRadius': '10px',
            'backgroundColor': '#ecf0f1',
            'boxShadow': '2px 2px 10px rgba(0,0,0,0.1)',
            'height': '80vh',
            # 'height': '100%',
            'overflowY': 'auto'
        }),

        html.Div([
            dcc.Graph(id='3d-plot', style={
                'height': '80%', 
                'borderRadius': '10px', 
                'boxShadow': '2px 2px 15px rgba(0,0,0,0.2)',
                'backgroundColor': 'white',
                'padding': '10px'
            }),
            html.Div(id='results-container', style={
                'height': '20%',
                'marginTop': '10px', 
                'padding': '10px', 
                'borderRadius': '10px',
                'backgroundColor': '#f9f9f9'
            }),
            html.Footer('© 2025 Pramod Kumar Yadav (@iAmPramodYadav)'),
        ], style={'width': '75%', 'height': '80vh',}),
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'gap': '20px', 'padding': '20px'})
])


# Function to format JSON with compact arrays
def format_json_compact_arrays(json_str):
    """
    Formats JSON string to make arrays more compact and readable.
    
    Args:
        json_str (str): JSON string to format
        
    Returns:
        str: Formatted JSON string with compact arrays
        
    The function:
    1. Identifies array patterns in the JSON
    2. Compacts multi-line arrays into single lines
    3. Preserves proper indentation for objects
    """
    # Use regex to find arrays and compact them
    # This pattern looks for array patterns with newlines and extra spaces
    pattern = r'\[\s*\n\s*([^][]*?)\s*\n\s*\]'
    
    # Function to process each match
    def compact_array(match):
        # Get the content of the array
        content = match.group(1)
        # Split by comma and newline, then clean each element
        elements = re.split(r',\s*\n\s*', content)
        elements = [elem.strip() for elem in elements]
        # Rejoin with comma and space
        return f"[{', '.join(elements)}]"
    
    # Apply the pattern repeatedly until no more changes
    prev_json = ""
    while prev_json != json_str:
        prev_json = json_str
        json_str = re.sub(pattern, compact_array, json_str, flags=re.DOTALL)
    
    return json_str
# ---------------------------------------- Callbacks ----------------------------------------
# Callback for gravity settings
@app.callback(
    Output('gravity-store', 'data'),
    [Input('gravity-value', 'value'),
     Input('gravity-x', 'value'),
     Input('gravity-y', 'value'),
     Input('gravity-z', 'value')],
    prevent_initial_call=True
)
def update_gravity_settings(gravity_value, gx, gy, gz):
    # Normalize direction vector
    direction = np.array([gx, gy, gz])
    norm = np.linalg.norm(direction)
    if norm > 0:
        direction = direction / norm
    
    return {
        'value': gravity_value if gravity_value is not None else 9.81,
        'direction': direction.tolist()
    }

# Callbacks for adding systems
@app.callback(
    Output('loads-store', 'data'),
    Input('add-load-btn', 'n_clicks'),
    State('loads-store', 'data'),
    prevent_initial_call=True
)
def add_load_system(n_clicks, data):
    new_load = {
        'name': f'Load System {len(data) + 1}',  # Default name
        'force': [0.0, 0.0, 0.0],
        'moment': [0.0, 0.0, 0.0],
        'euler_angles': [0.0, 0.0, 0.0],
        'rotation_order': 'xyz',
        'translation': [0.0, 0.0, 0.0],
        'color': {'hex': f'#{np.random.randint(0, 0xFFFFFF):06x}'},
        'mass': 0.0,
        'cog': [0.0, 0.0, 0.0]
    }
    return data + [new_load]

@app.callback(
    Output('targets-store', 'data'),
    Input('add-target-btn', 'n_clicks'),
    State('targets-store', 'data'),
    prevent_initial_call=True
)
def add_target_system(n_clicks, data):
    new_target = {
        'name': f'Target System {len(data) + 1}',  # Default name
        'euler_angles': [0.0, 0.0, 0.0],
        'rotation_order': 'xyz',
        'translation': [0.0, 0.0, 0.0],
        'color': {'hex': f'#{np.random.randint(0, 0xFFFFFF):06x}'}
    }
    return data + [new_target]

# Input components callback
@app.callback(
    [Output('load-inputs-container', 'children'),
     Output('target-inputs-container', 'children')],
    [Input('loads-store', 'data'),
     Input('targets-store', 'data')]
)
def update_input_components(loads, targets):
    def create_controls(items, input_type):
        controls = []
        for i, item in enumerate(items):
            # Handle legacy color format
            if isinstance(item['color'], str):
                item['color'] = {'hex': item['color']}

            system_color = item['color']['hex']

            controls.append(
                    html.Div([
                    html.H5(f"{input_type.capitalize()} System {i+1}"),
                    html.Div([
                        html.Label("System Name:"),
                        dcc.Input(
                            value=item.get('name', f'{input_type.capitalize()} System {i+1}'),
                            type='text',
                            id={'type': 'name', 'index': i, 'input-type': input_type},
                            style={'width': '200px'})
                    ], style={'marginBottom': '10px'}),
                        
                    html.Div([
                        html.Label("Position(X,Y,Z):"),
                        dcc.Input(value=item['translation'][0], type='number',
                                 id={'type': 'tx', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                        dcc.Input(value=item['translation'][1], type='number',
                                 id={'type': 'ty', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                        dcc.Input(value=item['translation'][2], type='number',
                                 id={'type': 'tz', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                    ], className='input-group',style={'display': 'flex', 'alignItems': 'center', 'gap': '5px'}),
                    # html.Hr(),
                    html.Div([
                        # Rotation order with inline label and dropdown
                        html.Div([
                            html.Label("Rotation Order:", style={'minWidth': '100px'}),
                            dcc.Dropdown(
                                options=['xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx'],
                                value=item['rotation_order'],
                                id={'type': 'rot-order', 'index': i, 'input-type': input_type},
                                style={'width': '120px'}
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'})
                    ], className='input-group', style={'flex': '1'}),
                        
                    html.Div([
                        # Rotation degrees with inline label and inputs
                        html.Div([
                            html.Label("Rotation (deg):", style={'minWidth': '100px'}),
                            html.Div([  # Container for inputs
                                dcc.Input(value=np.array(item['euler_angles'][0]), type='number',
                                         id={'type': 'rx', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                                dcc.Input(value=np.array(item['euler_angles'][1]), type='number',
                                         id={'type': 'ry', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                                dcc.Input(value=np.array(item['euler_angles'][2]), type='number',
                                         id={'type': 'rz', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                            ], style={'display': 'flex', 'gap': '5px'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'})
                    ], className='input-group', style={'flex': '1'}),
                    html.Hr(),
                        
                    html.Div([
                        html.Label("Force L(X,Y,Z):"),
                        dcc.Input(value=item.get('force', [0,0,0])[0], type='number',
                                 id={'type': 'fx', 'index': i, 'input-type': input_type}, style={'width': '50px'}),
                        dcc.Input(value=item.get('force', [0,0,0])[1], type='number',
                                 id={'type': 'fy', 'index': i, 'input-type': input_type}, style={'width': '50px'}),
                        dcc.Input(value=item.get('force', [0,0,0])[2], type='number',
                                 id={'type': 'fz', 'index': i, 'input-type': input_type}, style={'width': '50px'}),
                    ], className='input-group', style={'display': 'flex', 'alignItems': 'center', 'gap': '5px'}) if input_type == 'load' else html.Div(hidden=True),
                        
                    html.Div([
                        html.Label("Moment L(X,Y,Z):"),
                        dcc.Input(value=item.get('moment', [0,0,0])[0], type='number',
                                 id={'type': 'mx', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                        dcc.Input(value=item.get('moment', [0,0,0])[1], type='number',
                                 id={'type': 'my', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                        dcc.Input(value=item.get('moment', [0,0,0])[2], type='number',
                                 id={'type': 'mz', 'index': i, 'input-type': input_type},style={'width': '50px'}),
                    ], className='input-group', style={'display': 'flex', 'alignItems': 'center', 'gap': '5px'}) if input_type == 'load' else html.Div(hidden=True),
                    html.Hr(),
                   # Mass and COG inputs for load systems
                    html.Div([
                        html.Div([
                            html.Label("Mass (kg):"),
                            dcc.Input(value=item.get('mass', 0), type='number',
                                     id={'type': 'mass', 'index': i, 'input-type': input_type},
                                     style={'width': '80px'})
                        ], style={'marginBottom': '5px'}),

                        html.Div([
                            html.Label("CoG L(X,Y,Z):"),
                            dcc.Input(value=item.get('cog', [0,0,0])[0], type='number',
                                     id={'type': 'cog-x', 'index': i, 'input-type': input_type},
                                     style={'width': '50px'}),
                            dcc.Input(value=item.get('cog', [0,0,0])[1], type='number',
                                     id={'type': 'cog-y', 'index': i, 'input-type': input_type},
                                     style={'width': '50px'}),
                            dcc.Input(value=item.get('cog', [0,0,0])[2], type='number',
                                     id={'type': 'cog-z', 'index': i, 'input-type': input_type},
                                     style={'width': '50px'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '5px'})
                    ], style={'marginBottom': '10px'}) if input_type == 'load' else html.Div(hidden=True),

                ], style={
                    'border': f'2px solid {system_color}',
                    'borderRadius': '8px',
                    'padding': '8px',
                    'margin': '5px',
                    'boxShadow': '2px 2px 5px rgba(0,0,0,0.1)'
                })
            )
        return controls

    return create_controls(loads, 'load'), create_controls(targets, 'target')
# Input updates callback

@app.callback(
    [Output('loads-store', 'data', allow_duplicate=True),
     Output('targets-store', 'data', allow_duplicate=True)],
    [Input({'type': 'name', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'tx', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'ty', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'tz', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'rx', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'ry', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'rz', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'fx', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'fy', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'fz', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'mx', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'my', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'mz', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'mass', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'cog-x', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'cog-y', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'cog-z', 'index': ALL, 'input-type': ALL}, 'value'),
     Input({'type': 'rot-order', 'index': ALL, 'input-type': ALL}, 'value')],
    [State('loads-store', 'data'),
     State('targets-store', 'data')],
    prevent_initial_call=True
)
def update_stores(name, tx, ty, tz, rx, ry, rz, 
                 fx, fy, fz, mx, my, mz, 
                 mass, cog_x, cog_y, cog_z,
                 rot_orders,
                 loads, targets):
    ctx = dash.callback_context
    if not ctx.triggered:
        return loads, targets

    # Create dictionaries to store all input values by their type and index
    input_values = {'load': {}, 'target': {}}

    # Get the triggered input info
    triggered = [t['prop_id'] for t in ctx.triggered]
    
    # Process all inputs
    for trigger_idx, trigger in enumerate(triggered):
        # Parse the triggered component ID
        if '.' in trigger:  # Ensure it's a valid trigger
            component_id = trigger.split('.')[0]
            try:
                parsed_id = eval(component_id)
                input_type = parsed_id['input-type']
                index = parsed_id['index']
                value_type = parsed_id['type']
                
                # Initialize nested dictionaries if they don't exist
                if index not in input_values[input_type]:
                    input_values[input_type][index] = {}
                
                # Get the corresponding value from the triggered input
                value = ctx.triggered[trigger_idx]['value']
                # # Handle null/empty values for numeric inputs
                # if value_type in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'fx', 'fy', 'fz', 'mx', 'my', 'mz']:
                    # value = 0.0 if value is None or value == '' else float(value)
                # input_values[input_type][index][value_type] = value
                input_values[input_type][index][value_type] = value
                
            except Exception as e:
                print(f"Error processing trigger {trigger}: {e}")
                continue

    # Update loads
    for i in range(len(loads)):
        if i in input_values.get('load', {}):
            vals = input_values['load'][i]
            
            if 'name' in vals:
                loads[i]['name'] = vals['name']            
            # Update translation
            if any(k in vals for k in ['tx', 'ty', 'tz']):
                loads[i]['translation'] = [
                    vals.get('tx', loads[i]['translation'][0]),
                    vals.get('ty', loads[i]['translation'][1]),
                    vals.get('tz', loads[i]['translation'][2])
                ]
            
            # Update rotation angles
            if any(k in vals for k in ['rx', 'ry', 'rz']):
                loads[i]['euler_angles'] = np.array([
                    vals.get('rx', loads[i]['euler_angles'][0]),
                    vals.get('ry', loads[i]['euler_angles'][1]),
                    vals.get('rz', loads[i]['euler_angles'][2])
                ]).tolist()
            
            # Update force
            if any(k in vals for k in ['fx', 'fy', 'fz']):
                loads[i]['force'] = [
                    vals.get('fx', loads[i]['force'][0]),
                    vals.get('fy', loads[i]['force'][1]),
                    vals.get('fz', loads[i]['force'][2])
                ]
            
            # Update moment
            if any(k in vals for k in ['mx', 'my', 'mz']):
                loads[i]['moment'] = [
                    vals.get('mx', loads[i]['moment'][0]),
                    vals.get('my', loads[i]['moment'][1]),
                    vals.get('mz', loads[i]['moment'][2])
                ]
            
            # Update mass
            if 'mass' in vals:
                loads[i]['mass'] = vals['mass']
                
            # Update center of gravity
            if any(k in vals for k in ['cog-x', 'cog-y', 'cog-z']):
                loads[i]['cog'] = [
                    vals.get('cog-x', loads[i].get('cog', [0,0,0])[0]),
                    vals.get('cog-y', loads[i].get('cog', [0,0,0])[1]),
                    vals.get('cog-z', loads[i].get('cog', [0,0,0])[2])
                ]
            
            # Update rotation order
            if 'rot-order' in vals:
                loads[i]['rotation_order'] = vals['rot-order']

    # Update targets
    for i in range(len(targets)):
        if i in input_values.get('target', {}):
            vals = input_values['target'][i]
            if 'name' in vals:
                targets[i]['name'] = vals['name']       
            # Update translation
            if any(k in vals for k in ['tx', 'ty', 'tz']):
                targets[i]['translation'] = [
                    vals.get('tx', targets[i]['translation'][0]),
                    vals.get('ty', targets[i]['translation'][1]),
                    vals.get('tz', targets[i]['translation'][2])
                ]
            
            # Update rotation angles
            if any(k in vals for k in ['rx', 'ry', 'rz']):
                targets[i]['euler_angles'] = np.array([
                    vals.get('rx', targets[i]['euler_angles'][0]),
                    vals.get('ry', targets[i]['euler_angles'][1]),
                    vals.get('rz', targets[i]['euler_angles'][2])
                ]).tolist()
            
            # Update rotation order
            if 'rot-order' in vals:
                targets[i]['rotation_order'] = vals['rot-order']

    return loads, targets
# Visualization callback
@app.callback(
    [Output('3d-plot', 'figure'),
     Output('results-container', 'children')],
    [Input('loads-store', 'data'),
     Input('targets-store', 'data'),
     Input('gravity-store', 'data'),
     Input('theme-selector', 'value')]
)
def update_visualization(loads, 
                         targets,
                         gravity,
                         theme):
    fig = go.Figure()
    results = []
    theme_colors = PLOT_THEMES[theme]
    # Add global system
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers',
                              marker=dict(size=4, color='black'), name='Global'))

    # Add gravity vector
    gravity_value = gravity.get('value', 9.81)
    gravity_dir = np.array(gravity.get('direction', [0, 0, -1]))
    gravity_vec = gravity_value * gravity_dir
    
    # Add gravity vector to plot
    fig.add_trace(go.Scatter3d(
        x=[0, gravity_dir[0]], 
        y=[0, gravity_dir[1]], 
        z=[0, gravity_dir[2]],
        mode='lines',
        line=dict(color='purple', width=5),
        name=f'Gravity: {gravity_value} m/s²'
    ))

    # Process loads
    for i, load in enumerate(loads):
        try:
            load_name = load.get('name', f'Load System {i+1}')
            if isinstance(load['color'], str):  # Handle legacy format
                load['color'] = {'hex': load['color']}

            R, pos = rlt.create_rotation_matrix(
                np.radians(load['euler_angles']),
                # np.array(load['euler_angles']),
                load['rotation_order'],
                load['translation']
            )
            color = load['color']['hex']

            # Add coordinate system
            fig_load = plot3d.plot_triad(np.radians(load['euler_angles']), 
                                         load['rotation_order'],
                                         load['translation'], 
                                         tip_size = 0.5, len_triad = 1,colors_arr = color,
                                         triad_name = f"{load_name}:InputCSYS", legendgroup= f'group{i}')
            fig = go.Figure(data = fig.data + fig_load.data)
            # fig.add_traces(create_triad(pos, R, color))

            # Add vectors
            if 'force' in load:
                fig_force = plot3d.create_vector(pos, R @ load['force'], color, f'Force:{load["force"]}', legendgroup= f'force_group{i}',triad_name = f"{load_name}:Force")
                fig = go.Figure(data = fig.data + fig_force.data)
            if 'moment' in load:
                # fig.add_trace(create_vector(pos, R @ load['moment'], color, f'Load {i+1} Moment'))
                fig_mom  = plot3d.create_vector(pos, R @ load['moment'], color, f'Moment:{load["moment"]}', legendgroup= f'force_group{i}',triad_name = f"{load_name}:Moment")
                fig = go.Figure(data = fig.data + fig_mom.data)
            
            # Add gravity force vector to plot at COG position
            if 'mass' in load and load['mass'] > 0:
                                    # Get center of gravity or use load position if not specified
                cog = np.array(load.get('cog', [0, 0, 0]))
                if np.all(cog == 0):  # If COG is not specified, use load position
                    cog = load['translation']
                else:
                    # COG is specified relative to load coordinate system, transform to global
                    cog = load['translation'] + R @ cog

                fig.add_trace(go.Scatter3d(
                    x=[cog[0], cog[0] + gravity_dir[0]],
                    y=[cog[1], cog[1] + gravity_dir[1]],
                    z=[cog[2], cog[2] + gravity_dir[2]],
                    mode='lines',
                    line=dict(color=color, width=3, dash='dot'),
                    name=f'{load_name}: Gravity Force ({load["mass"]} kg)'
                ))

            # Add connection lines to all targets
            for j, target in enumerate(targets):
                # Create a slightly lighter version of the load color for the connection line
                line_color = color  # You can also create a lighter shade if desired  
                # Add connection line
                fig.add_trace(plot3d.create_connection_line(load['translation'],target['translation'],line_color))
        except Exception as e:
            print(f"Error processing load {i}: {e}")

    # Process targets
    for i, target in enumerate(targets):
        try:
            target_name = target.get('name', f'Target {i+1}')
            if isinstance(target['color'], str):  # Handle legacy format
                target['color'] = {'hex': target['color']}
            # target_name = load.get('name', f'Load System {i+1}')
            R_target, pos_target = rlt.create_rotation_matrix(
                np.radians(target['euler_angles']),
                # np.array(target['euler_angles']),
                target['rotation_order'],
                target['translation']
            )
            color = target['color']['hex']

            # Add coordinate system
            fig_load = plot3d.plot_triad(np.radians(target['euler_angles']), 
                                         target['rotation_order'],
                                         target['translation'], 
                                         tip_size = 0.5, len_triad = 1,colors_arr = color,
                                         triad_name = f"{target_name}:OutCSYS", legendgroup= f'Out_group{i}')
            fig = go.Figure(data = fig.data + fig_load.data)
            
            # fig.add_traces(create_triad(pos_target, R_target, color))

            # Calculate results
            total_F, total_M = np.zeros(3), np.zeros(3)
            for load in loads:
                R_load, pos_load = rlt.create_rotation_matrix(
                    np.radians(load['euler_angles']),
                    # np.array(load['euler_angles']),
                    load['rotation_order'],
                    load['translation']
                )
                
                # Calculate gravity force if mass is present
                gravity_force = np.zeros(3)
                gravity_moment = np.zeros(3)

                if 'mass' in load and load['mass'] > 0:
                    # Get center of gravity or use load position if not specified
                    cogL = np.array(load.get('cog', [0, 0, 0]))
                    if np.all(cogL == 0):  # If COG is not specified, use load position
                        cogg = load['translation']
                    else:
                        # COG is specified relative to load coordinate system, transform to global
                        cogg = load['translation'] + R_load @ cogL
                        
                    # Calculate gravity force in global coordinates
                    gravity_force_global = load['mass'] * gravity_value * gravity_dir
                    # Transform gravity force from global to load coordinate system
                    R_loadg, pos_loadg = rlt.create_rotation_matrix(np.radians(load['euler_angles']),load['rotation_order'],cogg)
                    gravity_force = R_loadg.T @ gravity_force_global
                    gravity_moment = np.cross(cogL, gravity_force_global)
                # Add gravity force to load force
                load_force = np.array(load.get('force', [0, 0, 0])) + gravity_force
                load_moment = np.array(load.get('moment', [0, 0, 0])) + gravity_moment

                F, M = rlt.rigid_load_transfer(
                    load_force,
                    load_moment,
                    R_load, pos_load,
                    R_target, pos_target
                )
                total_F += F
                total_M += M

            results.append({
                # 'System': f'Target {i+1}',
                'System': target.get('name', f'Target {i+1}'),
                'Fx': f"{total_F[0]:.2f}", 'Fy': f"{total_F[1]:.2f}", 'Fz': f"{total_F[2]:.2f}",
                'Mx': f"{total_M[0]:.2f}", 'My': f"{total_M[1]:.2f}", 'Mz': f"{total_M[2]:.2f}"
            })

        except Exception as e:
            print(f"Error processing target {i}: {e}")

    # Configure plot
    # Update layout with theme
    fig.update_layout(
        paper_bgcolor=theme_colors['bg_color'],
        plot_bgcolor=theme_colors['bg_color'],
        scene=dict(
            xaxis=dict(
                title='X',
                backgroundcolor=theme_colors['bg_color'],
                gridcolor=theme_colors['grid_color'],
                showbackground=True,
                zerolinecolor=theme_colors['grid_color'],
                color=theme_colors['text_color']
            ),
            yaxis=dict(
                title='Y',
                backgroundcolor=theme_colors['bg_color'],
                gridcolor=theme_colors['grid_color'],
                showbackground=True,
                zerolinecolor=theme_colors['grid_color'],
                color=theme_colors['text_color']
            ),
            zaxis=dict(
                title='Z',
                backgroundcolor=theme_colors['bg_color'],
                gridcolor=theme_colors['grid_color'],
                showbackground=True,
                zerolinecolor=theme_colors['grid_color'],
                color=theme_colors['text_color']
            ),
            aspectmode='cube',
            camera=dict(up=dict(x=0, y=0, z=1))
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        showlegend=True,
        scene_aspectmode='data',
        font=dict(color=theme_colors['text_color'])
    )
    dark_templates = ['dark','night']
    is_dark = theme in dark_templates 
    # # ----------------------------------------------------------
    # # Update layout with Plotly template
    # fig.update_layout(
    #     template=template,  # Use the selected Plotly template
    #     scene=dict(
    #         xaxis=dict(title='X'),
    #         yaxis=dict(title='Y'),
    #         zaxis=dict(title='Z'),
    #         aspectmode='cube',
    #         camera=dict(up=dict(x=0, y=0, z=1))
    #     ),
    #     margin=dict(l=0, r=0, b=0, t=30),
    #     showlegend=True,
    #     scene_aspectmode='data'
    # )

    # Create results table with styling based on template
    # dark_templates = ['plotly_dark']
    # is_dark = template in dark_templates
    # # ----------------------------------------------------------
    table = dash_table.DataTable(
        columns=[{'name': col, 'id': col} for col in ['System', 'Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']],
        data=results,
        style_cell={
            'textAlign': 'center',
            'padding': '5px',
            'backgroundColor': '#283442' if is_dark else 'white',
            'color': 'white' if is_dark else 'black'
        },
        style_header={
            'backgroundColor': '#3B4754' if is_dark else 'lightgrey',
            'fontWeight': 'bold',
            'color': 'white' if is_dark else 'black'
        },
        style_data_conditional=[{
            'if': {'row_index': 'odd'},
            'backgroundColor': '#3B4754' if is_dark else 'rgb(248, 248, 248)'
        }]
    )

    return fig, table

@app.callback(
    Output('download-data', 'data'),
    Input('export-btn', 'n_clicks'),
    [State('loads-store', 'data'),
     State('targets-store', 'data'),
     State('gravity-store', 'data'),
     State('export-format', 'value'),
     State('results-container', 'children')],
    prevent_initial_call=True
)
def export_data(n_clicks, loads, targets, gravity, export_format, results):
    if n_clicks is None:
        return dash.no_update
    
    # Create timestamp for filename
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Determine if we should use classic format based on user selection or auto-detection
    use_classic_format = export_format == 'classic'
    
    # If auto detection, check if targets came from edges
    if export_format == 'auto':
        use_classic_format = True
        # If any target has an 'edge_id' or comes from an edge, use new format
        for target in targets:
            if any(key in target for key in ['edge_id', 'source', 'target']):
                use_classic_format = False
                break
    
    if use_classic_format:
        # Export in classic RLT format (loads and targets)
        classic_data = {
            "loads": loads,
            "targets": targets,
            "gravity": gravity
        }
        
        # Export as JSON file in classic format
        json_filename = f"RLT_Data_{timestamp}.json"
        json_str = json.dumps(classic_data, indent=2)
        formatted_json = format_json_compact_arrays(json_str)
        return dict(content=formatted_json, filename=json_filename)
    else:
        # Create JSON structure matching the new format with nodes and edges
        json_data = {
            "metadata": {
                "version": "1.0",
                "coordinate_system": "right-handed",
                "units": {
                    "force": "N",
                    "moment": "Nm",
                    "mass": "kg",
                    "distance": "mm"
                },
                "description": "Data generated by Rigid Load Transfer Tool"
            },
            "nodes": [],
            "edges": [],
            "gravity": gravity
        }
        
        # Convert loads to nodes
        for i, load in enumerate(loads):
            node = {
                "id": load.get('id', f"n{i}"),
                "name": load.get('name', f'Load System {i+1}'),
                "color": load['color']['hex'],
                "mass": load.get('mass', 0.0),
                "cog": load.get('cog', [0.0, 0.0, 0.0]),
                "external_force": load.get('force', [0.0, 0.0, 0.0]),
                "moment": load.get('moment', [0.0, 0.0, 0.0]),
                "euler_angles": load.get('euler_angles', [0.0, 0.0, 0.0]),
                "rotation_order": load.get('rotation_order', 'xyz'),
                "translation": load.get('translation', [0.0, 0.0, 0.0]),
                "position": {"x": load.get('translation', [0, 0, 0])[0] * 10, 
                            "y": load.get('translation', [0, 0, 0])[1] * 10}
            }
            json_data["nodes"].append(node)
        
        # Convert targets to edges
        for i, target in enumerate(targets):
            # Use existing source/target if available, otherwise create a default connection
            source = target.get('source', f"n{i % len(json_data['nodes'])}")
            target_id = target.get('target', f"n{(i + 1) % len(json_data['nodes'])}")
            
            edge = {
                "id": target.get('edge_id', f"e{i}"),
                "source": source,
                "target": target_id,
                "interface_properties": {
                    "euler_angles": target.get('euler_angles', [0.0, 0.0, 0.0]),
                    "rotation_order": target.get('rotation_order', 'xyz'),
                    "position": target.get('translation', [0.0, 0.0, 0.0]),
                    "rlt_results": {
                        "force": [0.0, 0.0, 0.0],
                        "moment": [0.0, 0.0, 0.0],
                        "is_valid": True,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            }
            
            # If we have results, update the edge with calculated values
            if results and 'props' in results and 'data' in results['props'] and i < len(results['props']['data']):
                result_row = results['props']['data'][i]
                edge["interface_properties"]["rlt_results"]["force"] = [
                    float(result_row.get('Fx', '0').replace(',', '')),
                    float(result_row.get('Fy', '0').replace(',', '')),
                    float(result_row.get('Fz', '0').replace(',', ''))
                ]
                edge["interface_properties"]["rlt_results"]["moment"] = [
                    float(result_row.get('Mx', '0').replace(',', '')),
                    float(result_row.get('My', '0').replace(',', '')),
                    float(result_row.get('Mz', '0').replace(',', ''))
                ]
            
            json_data["edges"].append(edge)
        
        # Export as JSON file
        json_filename = f"RLT_Data_{timestamp}.json"
        json_str = json.dumps(json_data, indent=2)
        formatted_json = format_json_compact_arrays(json_str)
        return dict(content=formatted_json, filename=json_filename)


@app.callback(
    [Output('loads-store', 'data', allow_duplicate=True),
     Output('targets-store', 'data', allow_duplicate=True),
     Output('gravity-store', 'data', allow_duplicate=True)],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')],
    prevent_initial_call=True
)
def update_stores_from_file(contents, filename):
    if contents is None:
        return dash.no_update, dash.no_update, dash.no_update

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if filename.endswith('.json'):
            data = json.loads(decoded.decode('utf-8'))
            
            # Handle new JSON format with nodes and edges
            if 'nodes' in data and 'edges' in data:
                loads = []
                targets = []
                gravity_data = data.get('gravity', {'value': 9.81, 'direction': [0, 0, -1]})
                
                # Process nodes as loads
                node_id_map = {}  # To track node IDs and their index in the loads array
                for i, node in enumerate(data['nodes']):
                    # Extract node properties based on format
                    if 'data' in node:
                        # Old format with data nesting
                        node_data = node['data']
                    else:
                        # New format with properties at top level
                        node_data = node
                    
                    node_id = node_data.get('id', f'n{i}')
                    node_id_map[node_id] = len(loads)  # Track position in loads array
                    
                    # Create load system from node
                    load = {
                        'id': node_id,  # Store original id for reference
                        'name': node_data.get('name', node_data.get('id', f'Load {len(loads) + 1}')),
                        'force': node_data.get('external_force', node_data.get('force', [0.0, 0.0, 0.0])),
                        'moment': node_data.get('moment', [0.0, 0.0, 0.0]),
                        'euler_angles': node_data.get('euler_angles', [0.0, 0.0, 0.0]),
                        'rotation_order': node_data.get('rotation_order', 'xyz'),
                        'translation': node_data.get('translation', [0.0, 0.0, 0.0]),
                        'color': {'hex': node_data.get('color', f'#{np.random.randint(0, 0xFFFFFF):06x}')},
                        'mass': node_data.get('mass', 0.0),
                        'cog': node_data.get('cog', [0.0, 0.0, 0.0])
                    }
                    loads.append(load)
                
                # Process edges as targets
                for i, edge in enumerate(data['edges']):
                    # Extract edge properties based on format
                    if 'data' in edge:
                        # Old format with data nesting
                        edge_data = edge['data']
                    else:
                        # New format with properties at top level
                        edge_data = edge
                    
                    # Get interface properties
                    interface_props = edge_data.get('interface_properties', {})
                    
                    # Create target system from edge
                    target = {
                        'edge_id': edge_data.get('id', f'e{i}'),  # Store original edge id
                        'source': edge_data.get('source', ''),  # Store source node
                        'target': edge_data.get('target', ''),  # Store target node
                        'name': f'{edge_data.get("id", f"Edge {len(targets) + 1}")}',
                        'euler_angles': interface_props.get('euler_angles', [0.0, 0.0, 0.0]),
                        'rotation_order': interface_props.get('rotation_order', 'xyz'),
                        'translation': interface_props.get('position', [0.0, 0.0, 0.0]),
                        'color': {'hex': f'#{np.random.randint(0, 0xFFFFFF):06x}'}
                    }
                    targets.append(target)
                
                return loads, targets, gravity_data
            
            # Handle old format with loads and targets directly
            else:
                # No need to add edge info since this is classic format
                # Convert angles from degrees to radians (no conversion needed for new format)
                for load in data.get('loads', []):
                    if 'euler_angles' in load:
                        load['euler_angles'] = np.array(load['euler_angles']).tolist()
                
                for target in data.get('targets', []):
                    if 'euler_angles' in target:
                        target['euler_angles'] = np.array(target['euler_angles']).tolist()
                
                return data.get('loads', []), data.get('targets', []), data.get('gravity', {'value': 9.81, 'direction': [0, 0, -1]})
            
        else:
            raise ValueError("Unsupported file format")
    except Exception as e:
        print(f"Error parsing file: {e}")
        return dash.no_update, dash.no_update, dash.no_update

# Helper functions to handle both old and new JSON formats
def get_node_data(node):
    """Extract node data regardless of format (nested or flat)"""
    if "data" in node and isinstance(node["data"], dict):
        # Old format with nested data
        return node["data"]
    # New format with properties at top level
    return node

def get_edge_data(edge):
    """Extract edge source, target, id and interface properties from either format"""
    if "data" in edge and isinstance(edge["data"], dict):
        # Old format with nested data
        edge_data = edge["data"]
        # Check if interface properties are nested under data
        interface_props = edge_data.get("interface_properties", {})
        if not interface_props:
            # If not found, check for individual interface properties
            interface_props = {
                "euler_angles": edge_data.get("interface_euler_angles", [0.0, 0.0, 0.0]),
                "rotation_order": edge_data.get("interface_rotation_order", "xyz"),
                "position": edge_data.get("interface_position", [0.0, 0.0, 0.0]),
                "rlt_results": edge_data.get("rlt_results", {
                    "force": [0.0, 0.0, 0.0],
                    "moment": [0.0, 0.0, 0.0],
                    "is_valid": False,
                    "timestamp": None
                })
            }
        return {
            "id": edge_data.get("id", ""),
            "source": edge_data.get("source", ""),
            "target": edge_data.get("target", ""),
            "interface_properties": interface_props
        }
    
    # New format with properties at top level
    interface_props = edge.get("interface_properties", {})
    return {
        "id": edge.get("id", ""),
        "source": edge.get("source", ""),
        "target": edge.get("target", ""),
        "interface_properties": interface_props
    }

def extract_gravity_data(json_data):
    """Extract gravity information from JSON data"""
    gravity_data = {'value': 9.81, 'direction': [0, 0, -1]}
    
    if 'gravity' in json_data:
        gravity = json_data['gravity']
        if isinstance(gravity, dict):
            gravity_data['value'] = gravity.get('value', 9.81)
            gravity_data['direction'] = gravity.get('direction', [0, 0, -1])
    
    return gravity_data

# # Find a free port dynamically
# import webbrowser  # Add this line
# import socket
# def find_free_port():
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.bind(("", 0))  # Bind to any available port
#     port = sock.getsockname()[1]
#     sock.close()
#     return port
# if __name__ == '__main__':
#     # Use PORT from environment (for deployment) or find a free port locally
#     port = int(os.environ.get("PORT", find_free_port()))
    
#     # Open browser ONLY if running locally (not in production)
#     if os.environ.get("PORT") is None:
#         url = f"http://localhost:{port}"
#         webbrowser.open_new(url)  # Open browser before starting the server
#     # Start the server
#     app.run_server(host="0.0.0.0", port=port, debug=False)
if __name__ == '__main__':
    app.run_server(debug=True)