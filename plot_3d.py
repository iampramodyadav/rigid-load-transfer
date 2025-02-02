"""
@Author:    Pramod Kumar Yadav
@email:     pkyadav01234@gmail.com
@Date:      August, 2023
@status:    development
@PythonVersion: python3

"""
# Import dependencies
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, ALL
import plotly.graph_objects as go
import numpy as np
import json
import base64
import io
# import dash_daq as daq
import plot_3d as plot3d
import rigid_load_transfer as rlt
#---------------------------------------
# Calculation functions
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
# #---------------------------------------
# Visualization helpers
def create_vector(position, vector, color='red', name=None, legendgroup= None, triad_name=None):
    magnitude = np.linalg.norm(vector)
    # print(magnitude)
    scale = max(0.5, min(2.0, magnitude/10))  # Auto-scale based on magnitude
    
    if magnitude<1e-6:
        vector_x = 0.00
        vector_y = 0.00
        vector_z = 0.00
    else:
        vector_x = vector[0]/magnitude
        vector_y = vector[1]/magnitude
        vector_z = vector[2]/magnitude    
        
    x=float(position[0]) + vector_x*scale
    y=float(position[1]) + vector_y*scale
    z=float(position[2]) + vector_z*scale
    
    list_load = [[float(position[0]),float(position[1]),float(position[2])],[x,y,z]]
    # print(list_load)
    fig = plot_lines_from_points(list_load, colors_tip=[color],size_tip=0.3, tip_hover_text=[name], legendgroup = legendgroup,triad_name=triad_name)
    # fig = plot3d.plot_lines_from_points(list_load)
    fig.update_layout(showlegend=False)
    return fig 

def create_connection_line(start_point, end_point, color='gray'):
    """Create a dashed line connecting two points"""
    return go.Scatter3d(
        x=[start_point[0], end_point[0]],
        y=[start_point[1], end_point[1]],
        z=[start_point[2], end_point[2]],
        mode='lines',
        line=dict(
            color=color,
            dash='dot',  # 'dot', 'dash', 'dashdot'
            width=2
        ),
        showlegend=False
    )
# #---------------------------------------
def plot_3d_point(list):
    """
    Plots a 3D point cloud.

    Args:
        list (list): A list of 3D points, each point is a list of three numbers.

    Returns:
        None.
    """    
    x_data=[list[i][0] for i in range(len(list))]
    y_data=[list[i][1] for i in range(len(list))]
    z_data=[list[i][2] for i in range(len(list))]
    
    trace = go.Scatter3d(
        x=x_data,
        y=y_data,
        z=z_data,
        mode ='markers',
        marker = dict(size= 10,opacity= 0.9,color=z_data, colorscale='plotly3'))
    
    layout = go.Layout(margin={'l': 0, 'r': 0, 'b': 0, 't': 10})
    data = [trace]
    plot_figure = go.Figure(data=data, layout=layout)
    plot_figure.update_layout(width=600,height=500,)
    return plot_figure

def plot_arrow_tip(point_pair, sizetip=0.5, color='darkblue', name=None, showlegend=False, legendgroup=None,hover_text =None):
    """
    Plots a vector tip cone from head and tail.
    """
    x_data=[point_pair[i][0] for i in range(len(point_pair))]
    y_data=[point_pair[i][1] for i in range(len(point_pair))]
    z_data=[point_pair[i][2] for i in range(len(point_pair))]

    vec_cone = np.array(point_pair[1])-np.array(point_pair[0])
    vec_norm = np.linalg.norm(vec_cone)
    # print(f'cone: {vec_cone}, {vec_norm}')
    # print('vec_cone')
    # u = np.where(vec_norm != 0, vec_cone[0]/vec_norm, 0)#vec_cone[0]/vec_norm
    # v = np.where(vec_norm != 0, vec_cone[1]/vec_norm, 0)#vec_cone[1]/vec_norm
    # w = np.where(vec_norm != 0, vec_cone[2]/vec_norm, 0)#vec_cone[2]/vec_norm
    u = vec_cone[0]
    v = vec_cone[1]
    w = vec_cone[2]
    fig = go.Figure(data=go.Cone(
        x=[x_data[1]],
        y=[y_data[1]],
        z=[z_data[1]],
        u=[u],
        v=[v],
        w=[w],
        showscale=False,
        sizemode="scaled",
        sizeref=sizetip,
        anchor="tip",
        colorscale=[[0, color], [1, color]],
        hoverinfo='text',
        hovertext=hover_text,
        name=name,
        showlegend=showlegend,
        legendgroup=legendgroup))
    
    return fig
    
def plot_3d_line(point_list, color='darkblue', width=2, opacity=0.5, colorscale=None, name=None, 
                 legendgroup=None, show_legend=True, axis_labels=None):
    """
    Plots a 3D line.
    """
    x_data=[point_list[i][0] for i in range(len(point_list))]
    y_data=[point_list[i][1] for i in range(len(point_list))]
    z_data=[point_list[i][2] for i in range(len(point_list))]
    
    if axis_labels is None:
        axis_labels = ['x', 'y', 'z']
    
    hover_text = [f"{axis_labels[0]}: {x:.2f}<br>{axis_labels[1]}: {y:.2f}<br>{axis_labels[2]}: {z:.2f}" 
                 for x, y, z in zip(x_data, y_data, z_data)]
    
    marker_dict = dict(
        size=5,
        opacity=opacity
    )
    
    line_dict = dict(width=width)
    
    if colorscale:
        marker_dict.update(dict(
            color=z_data,
            colorscale=colorscale
        ))
        line_dict.update(dict(
            color=z_data,
            colorscale=colorscale
        ))
    else:
        line_dict.update(dict(color=color))
    
    trace=go.Scatter3d(
        x=x_data, 
        y=y_data, 
        z=z_data,
        marker=marker_dict,
        line=line_dict,
        name=name,
        legendgroup=legendgroup,
        showlegend=show_legend,
        hoverinfo='text',
        hovertext=hover_text,
        hoverlabel=dict(bgcolor='white')
    )
    
    layout = go.Layout(margin={'l': 0, 'r': 0, 'b': 0, 't': 30})
    data = [trace]
    plot_figure = go.Figure(data=data, layout=layout)
    plot_figure.update_layout(title = '3D Line Plot',width=500,height=400,)
    return plot_figure
    
def plot_lines_from_points(first_pair, *list_pair, size_tip=0.1, colors=None, colors_tip=None,
                         triad_name=None, title="3D Vector Plot", axis_labels=None, legendgroup=None, tip_hover_text =None):
    """
    Plots a series of 3D lines from a list of 3D points as a single triad.
    
    Args:
        first_pair (list): First list of 3D points that form a line.
        *list_pair: Additional lists of 3D points that form lines.
        size_tip (float): The size of the cone tip. (default=0.1)
        colors (list): List of colors for each line. If not provided, uses 'darkblue' for all lines.
        colors_tip (list): List of colors for arrow tips. If not provided, uses same colors as lines.
        triad_name (str): Name for the entire triad in legend. (default="Vector Triad")
        title (str): Title for the plot. (default="3D Vector Plot")
        axis_labels (list): Custom labels for x,y,z axes in hover text. (default=None)

    Returns:
        go.Figure.
    """
    if colors is None:
        colors = ['darkblue'] * (len(list_pair) + 1)
    
    if colors_tip is None:
        colors_tip = colors
        
    if axis_labels is None:
        axis_labels = ['x', 'y', 'z']
    if tip_hover_text is None:
        tip_hover_text = [f'vec{i}' for i in range(1,len(list_pair) + 2)]
    # print(tip_hover_text)
    fig1 = plot_3d_line(first_pair, color=colors[0], name=triad_name, 
                       legendgroup=legendgroup, show_legend=False, axis_labels=axis_labels)
    
    fig0 = plot_arrow_tip(first_pair, sizetip=size_tip, color=colors_tip[0], name=triad_name, 
                         showlegend=True, legendgroup=legendgroup, hover_text = tip_hover_text[0])
    
    fig = go.Figure(data=fig1.data + fig0.data)
    
    for i, pair in enumerate(list_pair, 1):
        fig1 = plot_3d_line(pair, color=colors[i], name=triad_name, 
                           legendgroup=legendgroup, show_legend=False, axis_labels=axis_labels)
        fig0 = plot_arrow_tip(pair, sizetip=size_tip, color=colors_tip[i], 
                            showlegend=False, legendgroup=legendgroup,hover_text = tip_hover_text[i])
        
        fig2 = go.Figure(data=fig.data + fig1.data + fig0.data)
        fig = fig2

    fig.update_layout(
        margin={'l': 0, 'r': 0, 'b': 0, 't': 30},
        title=title,
        width=700,
        height=400,
        showlegend=False,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255, 255, 255, 0.8)"
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        )
    )
    return fig
# def plot_lines_from_points(first_pair, *list_pair, size_tip=0.1, colors_line=None,  colors_tip=None, colorscale=None, names=None, title="3D Vector Plot"):
#     """
#     Plots a series of 3D lines from a list of 3D points.

#     Args:
#         first_pair (list): First list of 3D points that form a line.
#         *list_pair: Additional lists of 3D points that form lines.
#         size_tip (float): The size of the cone tip. (default=0.1)
#         colors (list): List of colors for each line. If not provided, uses 'darkblue' for all lines.
#         colorscale (str): Name of the colorscale to use. If provided, colors lines according to z values.
#         names (list): List of names for the legend. If not provided, uses "Line 1", "Line 2", etc.
#         title (str): Title for the plot. (default="3D Vector Plot")

#     Returns:
#         go.Figure.
#     """
#     if colors_line is None:
#         colors_line = ['darkblue'] * (len(list_pair) + 1)
        
#     if colors_tip is None:
#         colors_tip = ['darkblue'] * (len(list_pair) + 1)   
   
#     if names is None:
#         names = [f"Line {i+1}" for i in range(len(list_pair) + 1)]
    
#     # Create first line with legend entry
#     fig1 = plot_3d_line(first_pair, color=colors_line[0], colorscale=colorscale, name=names[0])
#     # Create arrow tip without legend entry
#     fig0 = plot_arrow_tip(first_pair, sizetip=size_tip, color=colors_tip[0], name=names[0], showlegend=False)
#     fig = go.Figure(data=fig1.data + fig0.data)
    
#     # Add remaining lines
#     for i, pair in enumerate(list_pair, 1):
#         fig1 = plot_3d_line(pair, color=colors_line[i], colorscale=colorscale, name=names[i])
#         fig0 = plot_arrow_tip(pair, sizetip=size_tip, color=colors_tip[i], name=names[i], showlegend=False)
        
#         fig2 = go.Figure(data=fig.data + fig1.data + fig0.data)
#         fig = fig2

#     # Update layout with legend configuration
#     fig.update_layout(
#         margin={'l': 0, 'r': 0, 'b': 0, 't': 30},
#         title=title,
#         width=700,
#         height=400,
#         showlegend=True,
#         legend=dict(
#             yanchor="top",
#             y=0.99,
#             xanchor="right",
#             x=0.99,
#             bgcolor="rgba(255, 255, 255, 0.8)"
#         )
#     )
#     return fig
def plot_triad(R, rotation_order, Position, colour_triad=['red', 'green', 'blue'], 
               colors_arr='magenta', tip_size=0.1, len_triad=1, triad_name = "Coordinate Triad", legendgroup = None):
    """
    Plots a coordinate system triad given rotation and position.
    
    Args:
        R (list): List of rotation angles in radians
        rotation_order (str): String specifying rotation order (e.g., 'xyz')
        Position (list): 3D position vector
        colour_triad (list): Colors for x,y,z axes. (default=['red', 'green', 'blue'])
        colors_arr (str): Color for arrow tips. (default='magenta')
        tip_size (float): Size of arrow tips. (default=0.1)
        len_triad (float): Length of triad axes. (default=1)
    
    Returns:
        go.Figure: Plotly figure object
    """
    R_A, pos = create_rotation_matrix(R, rotation_order, Position)
    x = R_A @ np.array([1,0,0])
    y = R_A @ np.array([0,1,0])
    z = R_A @ np.array([0,0,1])
    
    x = x*len_triad/np.linalg.norm(x)
    y = y*len_triad/np.linalg.norm(y)
    z = z*len_triad/np.linalg.norm(z)
    
    list1 = [pos, pos+x]
    list2 = [pos, pos+y]
    list3 = [pos, pos+z]

    fig = plot_lines_from_points(list1, list2, list3, 
                               size_tip=tip_size, 
                               colors=colour_triad, 
                               colors_tip=[colors_arr]*3,
                               triad_name=triad_name,  legendgroup = legendgroup, tip_hover_text = ['X','Y','Z'])
    # legend_color = colors_arr
    # If a specific legend color is provided, modify traces
    # if legend_color:
    #     for trace in fig.data:
    #         if trace.name == triad_name:
    #             # Handle Scatter3d traces (lines)
    #             # if hasattr(trace, 'line'):
    #             #     trace.line.color = legend_color
    #             if hasattr(trace, 'marker'):
    #                 trace.marker.color = legend_color
                
    #             # Handle Cone traces (arrow tips)
    #             if hasattr(trace, 'colorscale'):
    #                 trace.colorscale = [[0, legend_color], [1, legend_color]]
    
    fig.update_layout(scene_aspectmode='data')
    return fig
#---------------------------------------

def surf_plot(x_data, y_data, z_data):
    """
    Plots a 3D surface plot.

    Args:
        x_data (list): A list of x-coordinates.
        y_data (list): A list of y-coordinates.
        z_data (list): A list of z-coordinates.
    Returns:
        go.Figure.
    """
    
    trace = go.Surface(x = x_data, y = y_data, z =z_data )    
    # Configure the layout.
    data = [trace]
    layout = go.Layout(title = '3D Surface plot',width=700,height=400,margin={'l': 0, 'r': 0, 'b': 0, 't': 30})
    fig = go.Figure(data = data, layout=layout)
    fig.show()
    
#---------------------------------------
def plot_surf(A=1, B=1, n=1, m=1, D=0, p=1, x_lim=[-10, 10], y_lim=[-10, 10]):
    """
    $z = (D-Ax^n+By^m)^p$

    """
    x = np.linspace(x_lim[0], x_lim[1], 100)
    y = np.linspace(y_lim[0], y_lim[1], 100)

    xGrid, yGrid = np.meshgrid(y, x)

    z = (D + A * xGrid**n + B * yGrid**m) ** p
    fig = go.Figure()

    fig.add_trace(
        go.Surface(x=x, y=y, z=z, colorscale="Viridis", showscale=False),
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "b": 0, "t": 30},
        title="3D Surface Plot",
        width=800,
        height=600,
    )

    return fig
if __name__ == "__main__":
    #------------------------------
    list_point=[[1,3,3],
          [4,3,6],
          [7,5,9],
          [10,11,13]]
    fig1=plot_3d_point(list_point)
    fig1.show()
    #------------------------------
    list1=[[0,0,0],[2,1,1]]
    fig0=plot_arrow_tip(list1)
    fig0.show()
    #------------------------------
    list=[[1,2,3],[4,6,6],[7,8,9],[10,11,12],[2,5,6]]
    fig2=plot_3d_line(list)
    fig2.show()
    #------------------------------
    list1=[[0,0,0],[1,0,0]]
    list2=[[0,0,0],[0,1,0]]   
    list3=[[0,0,0],[0,0,1]] 
    list4=[[0,0,0],[1,1,1]]
    fig3=plot_lines_from_points(list1,list2,list3,list4)
    fig3.show()
    #------------------------------
    fig1 = plot_surf(A=1, B=1, n=2, m=2, D=0, p=1, x_lim=[-100, 100], y_lim=[-100, 100])
    fig1.show()




