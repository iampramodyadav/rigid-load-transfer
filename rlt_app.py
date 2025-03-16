import sys
import json
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QLineEdit, QScrollArea, QFileDialog,
                               QTableWidget, QTableWidgetItem, QSplitter, QComboBox)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, Signal, QObject
import plotly.graph_objects as go
import rigid_load_transfer as rlt
import plot_3d as plot3d

class SystemEmitter(QObject):
    data_changed = Signal()

class SystemInputWidget(QWidget):
    def __init__(self, system_type, index, initial_data, emitter, parent=None):
        super().__init__(parent)
        self.system_type = system_type
        self.index = index
        self.emitter = emitter
        self.init_ui(initial_data)
        
    def init_ui(self, data):
        layout = QVBoxLayout()
        self.setStyleSheet("""
            QWidget {
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }
        """)
        
        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(data.get('name', f'{self.system_type} System {self.index+1}'))
        self.name_input.textChanged.connect(self.emit_changes)
        name_layout.addWidget(self.name_input)
        
        # Position inputs
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position (X,Y,Z):"))
        self.tx = QLineEdit(str(data['translation'][0]))
        self.ty = QLineEdit(str(data['translation'][1]))
        self.tz = QLineEdit(str(data['translation'][2]))
        for inp in [self.tx, self.ty, self.tz]:
            inp.setFixedWidth(60)
            inp.textChanged.connect(self.emit_changes)
            pos_layout.addWidget(inp)
        
        # Rotation order
        rot_order_layout = QHBoxLayout()
        rot_order_layout.addWidget(QLabel("Rotation Order:"))
        self.rot_order = QComboBox()
        self.rot_order.addItems(['xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx'])
        self.rot_order.setCurrentText(data['rotation_order'])
        self.rot_order.currentTextChanged.connect(self.emit_changes)
        rot_order_layout.addWidget(self.rot_order)
        
        # Rotation inputs
        rot_layout = QHBoxLayout()
        rot_layout.addWidget(QLabel("Rotation (deg):"))
        self.rx = QLineEdit(str(data['euler_angles'][0]))
        self.ry = QLineEdit(str(data['euler_angles'][1]))
        self.rz = QLineEdit(str(data['euler_angles'][2]))
        for inp in [self.rx, self.ry, self.rz]:
            inp.setFixedWidth(60)
            inp.textChanged.connect(self.emit_changes)
            rot_layout.addWidget(inp)
        
        # Force inputs (only for load systems)
        if self.system_type == 'load':
            force_layout = QHBoxLayout()
            force_layout.addWidget(QLabel("Force (X,Y,Z):"))
            self.fx = QLineEdit(str(data['force'][0]))
            self.fy = QLineEdit(str(data['force'][1]))
            self.fz = QLineEdit(str(data['force'][2]))
            for inp in [self.fx, self.fy, self.fz]:
                inp.setFixedWidth(60)
                inp.textChanged.connect(self.emit_changes)
                force_layout.addWidget(inp)
            
            moment_layout = QHBoxLayout()
            moment_layout.addWidget(QLabel("Moment (X,Y,Z):"))
            self.mx = QLineEdit(str(data['moment'][0]))
            self.my = QLineEdit(str(data['moment'][1]))
            self.mz = QLineEdit(str(data['moment'][2]))
            for inp in [self.mx, self.my, self.mz]:
                inp.setFixedWidth(60)
                inp.textChanged.connect(self.emit_changes)
                moment_layout.addWidget(inp)
        
        # Assemble layout
        layout.addLayout(name_layout)
        layout.addLayout(pos_layout)
        layout.addLayout(rot_order_layout)
        layout.addLayout(rot_layout)
        if self.system_type == 'load':
            layout.addLayout(force_layout)
            layout.addLayout(moment_layout)
        
        self.setLayout(layout)
    
    def emit_changes(self):
        self.emitter.data_changed.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loads = []
        self.targets = []
        self.emitter = SystemEmitter()
        self.emitter.data_changed.connect(self.update_plot)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Rigid Load Transfer Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Load systems
        load_header = QHBoxLayout()
        load_header.addWidget(QLabel("Load Systems"))
        self.add_load_btn = QPushButton("➕ Add Load System")
        self.add_load_btn.clicked.connect(self.add_load_system)
        load_header.addWidget(self.add_load_btn)
        
        self.loads_scroll = QScrollArea()
        self.loads_container = QWidget()
        self.loads_layout = QVBoxLayout()
        self.loads_container.setLayout(self.loads_layout)
        self.loads_scroll.setWidget(self.loads_container)
        self.loads_scroll.setWidgetResizable(True)
        
        # Target systems
        target_header = QHBoxLayout()
        target_header.addWidget(QLabel("Target Systems"))
        self.add_target_btn = QPushButton("➕ Add Target System")
        self.add_target_btn.clicked.connect(self.add_target_system)
        target_header.addWidget(self.add_target_btn)
        
        self.targets_scroll = QScrollArea()
        self.targets_container = QWidget()
        self.targets_layout = QVBoxLayout()
        self.targets_container.setLayout(self.targets_layout)
        self.targets_scroll.setWidget(self.targets_container)
        self.targets_scroll.setWidgetResizable(True)
        
        # Assemble left panel
        left_layout.addLayout(load_header)
        left_layout.addWidget(self.loads_scroll)
        left_layout.addLayout(target_header)
        left_layout.addWidget(self.targets_scroll)
        left_widget.setLayout(left_layout)
        
        # Right panel
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Plot view
        self.web_view = QWebEngineView()
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(
            ["System", "Fx", "Fy", "Fz", "Mx", "My", "Mz"]
        )
        
        right_layout.addWidget(self.web_view, 3)
        right_layout.addWidget(self.results_table, 1)
        right_widget.setLayout(right_layout)
        
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([400, 800])
        
        self.setCentralWidget(main_splitter)
        
        # Add initial systems
        self.add_load_system()
        self.add_target_system()
        
    def add_load_system(self):
        new_load = {
            'name': f'Load System {len(self.loads)+1}',
            'force': [0.0, 0.0, 0.0],
            'moment': [0.0, 0.0, 0.0],
            'euler_angles': [0.0, 0.0, 0.0],
            'rotation_order': 'xyz',
            'translation': [0.0, 0.0, 0.0]
        }
        self.loads.append(new_load)
        widget = SystemInputWidget('load', len(self.loads)-1, new_load, self.emitter)
        self.loads_layout.addWidget(widget)
        
    def add_target_system(self):
        new_target = {
            'name': f'Target System {len(self.targets)+1}',
            'euler_angles': [0.0, 0.0, 0.0],
            'rotation_order': 'xyz',
            'translation': [0.0, 0.0, 0.0]
        }
        self.targets.append(new_target)
        widget = SystemInputWidget('target', len(self.targets)-1, new_target, self.emitter)
        self.targets_layout.addWidget(widget)
    
    def get_current_data(self):
        # Update loads data
        for i in range(self.loads_layout.count()):
            widget = self.loads_layout.itemAt(i).widget()
            if isinstance(widget, SystemInputWidget):
                self.loads[i] = {
                    'name': widget.name_input.text(),
                    'translation': [
                        float(widget.tx.text() or 0),
                        float(widget.ty.text() or 0),
                        float(widget.tz.text() or 0)
                    ],
                    'rotation_order': widget.rot_order.currentText(),
                    'euler_angles': [
                        float(widget.rx.text() or 0),
                        float(widget.ry.text() or 0),
                        float(widget.rz.text() or 0)
                    ],
                    'force': [
                        float(widget.fx.text() or 0),
                        float(widget.fy.text() or 0),
                        float(widget.fz.text() or 0)
                    ],
                    'moment': [
                        float(widget.mx.text() or 0),
                        float(widget.my.text() or 0),
                        float(widget.mz.text() or 0)
                    ]
                }
        
        # Update targets data
        for i in range(self.targets_layout.count()):
            widget = self.targets_layout.itemAt(i).widget()
            if isinstance(widget, SystemInputWidget):
                self.targets[i] = {
                    'name': widget.name_input.text(),
                    'translation': [
                        float(widget.tx.text() or 0),
                        float(widget.ty.text() or 0),
                        float(widget.tz.text() or 0)
                    ],
                    'rotation_order': widget.rot_order.currentText(),
                    'euler_angles': [
                        float(widget.rx.text() or 0),
                        float(widget.ry.text() or 0),
                        float(widget.rz.text() or 0)
                    ]
                }
        
        return self.loads, self.targets
    
    def update_plot(self):
        loads, targets = self.get_current_data()
        fig = go.Figure()
        results = []
        
        # Add global system
        fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers',
                                  marker=dict(size=4, color='black'), name='Global'))
        
        # Process loads
        for i, load in enumerate(loads):
            try:
                R, pos = rlt.create_rotation_matrix(
                    np.radians(load['euler_angles']),
                    load['rotation_order'],
                    load['translation']
                )
                
                # Add coordinate system
                fig_load = plot3d.plot_triad(
                    np.radians(load['euler_angles']),
                    load['rotation_order'],
                    load['translation'],
                    tip_size=0.5,
                    len_triad=1,
                    colors_arr='#3498db',
                    triad_name=f"{load['name']}:InputCSYS"
                )
                fig.add_traces(fig_load.data)
                
                # Add vectors
                if 'force' in load:
                    fig_force = plot3d.create_vector(
                        pos, R @ load['force'], '#e74c3c',
                        f"Force:{load['force']}", triad_name=f"{load['name']}:Force"
                    )
                    fig.add_traces(fig_force.data)
                
                if 'moment' in load:
                    fig_mom = plot3d.create_vector(
                        pos, R @ load['moment'], '#2ecc71',
                        f"Moment:{load['moment']}", triad_name=f"{load['name']}:Moment"
                    )
                    fig.add_traces(fig_mom.data)
                
            except Exception as e:
                print(f"Error processing load {i}: {e}")
        
        # Process targets and calculate results
        self.results_table.setRowCount(len(targets))
        for i, target in enumerate(targets):
            try:
                R_target, pos_target = rlt.create_rotation_matrix(
                    np.radians(target['euler_angles']),
                    target['rotation_order'],
                    target['translation']
                )
                
                # Add coordinate system
                fig_target = plot3d.plot_triad(
                    np.radians(target['euler_angles']),
                    target['rotation_order'],
                    target['translation'],
                    tip_size=0.5,
                    len_triad=1,
                    colors_arr='#f1c40f',
                    triad_name=f"{target['name']}:OutCSYS"
                )
                fig.add_traces(fig_target.data)
                
                # Calculate results
                total_F, total_M = np.zeros(3), np.zeros(3)
                for load in loads:
                    R_load, pos_load = rlt.create_rotation_matrix(
                        np.radians(load['euler_angles']),
                        load['rotation_order'],
                        load['translation']
                    )
                    F, M = rlt.rigid_load_transfer(
                        np.array(load['force']),
                        np.array(load['moment']),
                        R_load, pos_load,
                        R_target, pos_target
                    )
                    total_F += F
                    total_M += M
                
                # Update results table
                self.results_table.setItem(i, 0, QTableWidgetItem(target['name']))
                for col, val in enumerate(total_F, 1):
                    self.results_table.setItem(i, col, QTableWidgetItem(f"{val:.2f}"))
                for col, val in enumerate(total_M, 4):
                    self.results_table.setItem(i, col, QTableWidgetItem(f"{val:.2f}"))
                
            except Exception as e:
                print(f"Error processing target {i}: {e}")
        
        # Update plot layout
        fig.update_layout(
            scene=dict(
                xaxis=dict(title='X'),
                yaxis=dict(title='Y'),
                zaxis=dict(title='Z'),
                aspectmode='cube',
                camera=dict(up=dict(x=0, y=0, z=1))
            ),
            margin=dict(l=0, r=0, b=0, t=30),
            showlegend=True,
            scene_aspectmode='data'
        )
        
        # Display plot in web view
        self.web_view.setHtml(fig.to_html(include_plotlyjs='cdn'))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())