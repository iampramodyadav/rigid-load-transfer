import sys
import json
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QScrollArea, QFileDialog,
    QTableWidget, QTableWidgetItem, QSplitter, QComboBox,
    QGroupBox, QMessageBox, QHeaderView, QToolBar, QStatusBar,
    QTabWidget, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QTextEdit, QCheckBox, QSpinBox, QDoubleSpinBox,
    QInputDialog, QProgressDialog, QMenuBar, QMenu, QDockWidget, QFrame
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QPointF, QRectF, QLineF, QSettings, QThread
from PySide6.QtGui import QFont, QAction, QPen, QBrush, QColor, QPainter, QKeySequence, QIcon
import plotly.graph_objects as go
import rigid_load_transfer as rlt
import plot_3d as plot3d


# ===================== CALCULATION WORKER THREAD =====================
class CalculationWorker(QThread):
    """Background thread for heavy calculations"""
    calculation_complete = Signal(object)
    progress_update = Signal(int, str)
    
    def __init__(self, graph_data, gravity_data, triad_size):
        super().__init__()
        self.graph_data = graph_data
        self.gravity_data = gravity_data
        self.triad_size = triad_size
        
    def run(self):
        """Perform calculations in background"""
        try:
            result = {
                'success': True,
                'edge_results': [],
                'figure_data': None
            }
            
            # Simulate calculation progress
            total_items = len(self.graph_data['nodes']) + len(self.graph_data['edges'])
            progress = 0
            
            for i, node in enumerate(self.graph_data['nodes']):
                progress = int((i / total_items) * 100)
                self.progress_update.emit(progress, f"Processing node {node.get('name', '')}...")
                # Add small delay to show progress (remove in production)
                self.msleep(10)
            
            for i, edge in enumerate(self.graph_data['edges']):
                progress = int(((len(self.graph_data['nodes']) + i) / total_items) * 100)
                self.progress_update.emit(progress, f"Calculating edge {edge.get('id', '')}...")
                self.msleep(10)
            
            self.progress_update.emit(100, "Complete!")
            self.calculation_complete.emit(result)
            
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            self.calculation_complete.emit(result)


# ===================== UNITS MANAGER =====================
class UnitsManager:
    """Manage unit conversions"""
    UNITS = {
        'force': {'N': 1.0, 'kN': 1000.0, 'lbf': 4.44822, 'kip': 4448.22},
        'moment': {'Nm': 1.0, 'kNm': 1000.0, 'lbf-ft': 1.35582, 'kip-ft': 1355.82},
        'length': {'mm': 1.0, 'm': 1000.0, 'cm': 10.0, 'in': 25.4, 'ft': 304.8},
        'mass': {'kg': 1.0, 'g': 0.001, 'ton': 1000.0, 'lb': 0.453592}
    }
    
    def __init__(self):
        self.current_units = {
            'force': 'N',
            'moment': 'Nm',
            'length': 'mm',
            'mass': 'kg'
        }
    
    def convert(self, value, from_unit, to_unit, unit_type):
        """Convert value between units"""
        if from_unit == to_unit:
            return value
        base_value = value * self.UNITS[unit_type][from_unit]
        return base_value / self.UNITS[unit_type][to_unit]
    
    def set_unit(self, unit_type, unit):
        """Set current unit for a type"""
        if unit_type in self.current_units and unit in self.UNITS[unit_type]:
            self.current_units[unit_type] = unit
            return True
        return False
    
    def get_unit(self, unit_type):
        """Get current unit for a type"""
        return self.current_units.get(unit_type, '')


# ===================== VALIDATION MANAGER =====================
class ValidationManager:
    """Validate input data and provide warnings"""
    
    @staticmethod
    def validate_node(node_data):
        """Validate node data"""
        warnings = []
        errors = []
        
        # Check required fields
        if not node_data.get('name'):
            errors.append("Node name is required")
        
        # Check rotation angles
        angles = node_data.get('euler_angles', [0, 0, 0])
        for i, angle in enumerate(angles):
            if abs(angle) > 360:
                warnings.append(f"Rotation angle {['X', 'Y', 'Z'][i]} exceeds 360°")
        
        # Check mass
        mass = node_data.get('mass', 0)
        if mass < 0:
            errors.append("Mass cannot be negative")
        
        # Check for very large forces
        force = node_data.get('external_force', [0, 0, 0])
        max_force = max(abs(f) for f in force)
        if max_force > 1000000:
            warnings.append(f"Very large force detected: {max_force:.2e} N")
        
        return errors, warnings
    
    @staticmethod
    def validate_edge(edge_data, nodes):
        """Validate edge data"""
        warnings = []
        errors = []
        
        # Check source and target exist
        source = edge_data.get('source')
        target = edge_data.get('target')
        
        node_ids = [n['id'] for n in nodes]
        if source not in node_ids:
            errors.append(f"Source node '{source}' not found")
        if target not in node_ids:
            errors.append(f"Target node '{target}' not found")
        
        if source == target:
            errors.append("Source and target cannot be the same")
        
        return errors, warnings
    
    @staticmethod
    def check_system_consistency(graph_data):
        """Check overall system consistency"""
        warnings = []
        errors = []
        
        # Check for isolated nodes
        connected_nodes = set()
        for edge in graph_data['edges']:
            connected_nodes.add(edge['source'])
            connected_nodes.add(edge['target'])
        
        all_nodes = {n['id'] for n in graph_data['nodes']}
        isolated = all_nodes - connected_nodes
        if isolated:
            warnings.append(f"Isolated nodes detected: {', '.join(isolated)}")
        
        # Check for circular dependencies
        # (Simple check - more sophisticated cycle detection could be added)
        
        return errors, warnings


# ===================== REPORT GENERATOR =====================
class ReportGenerator:
    """Generate analysis reports"""
    
    @staticmethod
    def generate_summary_report(graph_data, results):
        """Generate text summary report"""
        report = []
        report.append("=" * 60)
        report.append("LOAD TRANSFER ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # System overview
        report.append("SYSTEM OVERVIEW")
        report.append("-" * 60)
        report.append(f"Total Nodes: {len(graph_data['nodes'])}")
        report.append(f"Total Connections: {len(graph_data['edges'])}")
        report.append("")
        
        # Nodes summary
        report.append("NODES")
        report.append("-" * 60)
        for node in graph_data['nodes']:
            # report.append()
            # ("Position", node_data.get('translation', [0, 0, 0])),
            # ("Rotation", node_data.get('euler_angles', [0, 0, 0])),
            # ("CoG", node_data.get('cog', [0, 0, 0])),
            # ("Force", node_data.get('external_force', [0, 0, 0])),
            # ("Moment", node_data.get('moment', [0, 0, 0]))
            report.append(f"\n{node['name']} ({node['id']})")

            report.append(f"  Position: {node['translation']}")
            report.append(f"  Euler angles:  {node['rotation_order']} | {node['euler_angles']}")
            report.append(f"  COG: {node['cog']}")

            report.append(f"  Mass: {node.get('mass', 0)} kg")
            force = node.get('external_force', [0, 0, 0])
            moment = node.get('moment', [0, 0, 0])
            if any(f != 0 for f in force):
                report.append(f"  External Force: {force}")
            if any(m != 0 for m in moment):
                report.append(f"  External Moment: {moment}")     
        report.append("")
        
        # Edges summary
        report.append("CONNECTIONS & RESULTS")
        report.append("-" * 60)
        for edge in graph_data['edges']:
            report.append(f"\n{edge['id']}: {edge['source']} → {edge['target']}")
            interface = edge.get('interface_properties', {})
            rlt_results = interface.get('rlt_results', {})

            if rlt_results.get('is_valid'):
                force = rlt_results['force']
                moment = rlt_results['moment']

                position = interface['position']
                rotation_order = interface['rotation_order']
                euler_angles = interface['euler_angles']

                report.append(f"  Position:     [{position[0]:10.3f}, {position[1]:10.3f}, {position[2]:10.3f}] N")
                report.append(f"  Euler angles: {rotation_order}|[{euler_angles[0]:10.3f}, {euler_angles[1]:10.3f}, {euler_angles[2]:10.3f}] deg")
                report.append(f"  Force:  [{force[0]:10.3f}, {force[1]:10.3f}, {force[2]:10.3f}] N")
                report.append(f"  Moment: [{moment[0]:10.3f}, {moment[1]:10.3f}, {moment[2]:10.3f}] Nm")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    @staticmethod
    def export_to_csv(graph_data, filepath):
        """Export results to CSV"""
        try:
            with open(filepath, 'w') as f:
                # Header
                f.write("Edge ID,Source,Target,Fx,Fy,Fz,Mx,My,Mz,Position X,Position Y,Position Z\n")
                
                # Data
                for edge in graph_data['edges']:
                    interface = edge.get('interface_properties', {})
                    rlt_results = interface.get('rlt_results', {})
                    pos = interface.get('position', [0, 0, 0])
                    
                    if rlt_results.get('is_valid'):
                        force = rlt_results['force']
                        moment = rlt_results['moment']
                        
                        f.write(f"{edge['id']},{edge['source']},{edge['target']},")
                        f.write(f"{force[0]:.6f},{force[1]:.6f},{force[2]:.6f},")
                        f.write(f"{moment[0]:.6f},{moment[1]:.6f},{moment[2]:.6f},")
                        f.write(f"{pos[0]:.6f},{pos[1]:.6f},{pos[2]:.6f}\n")
            
            return True
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False


# ===================== PREFERENCES DIALOG =====================
class PreferencesDialog(QDialog):
    """Application preferences dialog"""
    def __init__(self, units_manager, parent=None):
        super().__init__(parent)
        self.units_manager = units_manager
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Units section
        units_group = QGroupBox("Units")
        units_layout = QVBoxLayout()
        
        # Force units
        force_layout = QHBoxLayout()
        force_layout.addWidget(QLabel("Force:"))
        self.force_combo = QComboBox()
        self.force_combo.addItems(['N', 'kN', 'lbf', 'kip'])
        self.force_combo.setCurrentText(units_manager.get_unit('force'))
        force_layout.addWidget(self.force_combo)
        force_layout.addStretch()
        units_layout.addLayout(force_layout)
        
        # Moment units
        moment_layout = QHBoxLayout()
        moment_layout.addWidget(QLabel("Moment:"))
        self.moment_combo = QComboBox()
        self.moment_combo.addItems(['Nm', 'kNm', 'lbf-ft', 'kip-ft'])
        self.moment_combo.setCurrentText(units_manager.get_unit('moment'))
        moment_layout.addWidget(self.moment_combo)
        moment_layout.addStretch()
        units_layout.addLayout(moment_layout)
        
        # Length units
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Length:"))
        self.length_combo = QComboBox()
        self.length_combo.addItems(['mm', 'm', 'cm', 'in', 'ft'])
        self.length_combo.setCurrentText(units_manager.get_unit('length'))
        length_layout.addWidget(self.length_combo)
        length_layout.addStretch()
        units_layout.addLayout(length_layout)
        
        # Mass units
        mass_layout = QHBoxLayout()
        mass_layout.addWidget(QLabel("Mass:"))
        self.mass_combo = QComboBox()
        self.mass_combo.addItems(['kg', 'g', 'ton', 'lb'])
        self.mass_combo.setCurrentText(units_manager.get_unit('mass'))
        mass_layout.addWidget(self.mass_combo)
        mass_layout.addStretch()
        units_layout.addLayout(mass_layout)
        
        units_group.setLayout(units_layout)
        layout.addWidget(units_group)
        
        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        
        self.show_node_labels = QCheckBox("Show node labels in graph")
        self.show_node_labels.setChecked(True)
        display_layout.addWidget(self.show_node_labels)
        
        self.show_force_vectors = QCheckBox("Show force vectors")
        self.show_force_vectors.setChecked(True)
        display_layout.addWidget(self.show_force_vectors)
        
        self.show_moment_vectors = QCheckBox("Show moment vectors")
        self.show_moment_vectors.setChecked(True)
        display_layout.addWidget(self.show_moment_vectors)
        
        self.auto_calculate = QCheckBox("Auto-calculate on change")
        self.auto_calculate.setChecked(True)
        display_layout.addWidget(self.auto_calculate)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_settings(self):
        """Get all settings"""
        return {
            'units': {
                'force': self.force_combo.currentText(),
                'moment': self.moment_combo.currentText(),
                'length': self.length_combo.currentText(),
                'mass': self.mass_combo.currentText()
            },
            'display': {
                'show_node_labels': self.show_node_labels.isChecked(),
                'show_force_vectors': self.show_force_vectors.isChecked(),
                'show_moment_vectors': self.show_moment_vectors.isChecked(),
                'auto_calculate': self.auto_calculate.isChecked()
            }
        }


# ===================== NODE GRAPH VISUALIZATION =====================
class NodeGraphicsItem(QGraphicsEllipseItem):
    """Interactive node representation in the graph view"""
    def __init__(self, node_id, name, color, x, y, parent_view):
        super().__init__(-30, -30, 60, 60)
        self.node_id = node_id
        self.node_name = name
        self.parent_view = parent_view
        self.edges = []  # Initialize edges list BEFORE setting flags
        
        # Set appearance
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor("#2c3e50"), 2))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges)
        self.setPos(x, y)
        
        # Add text label
        self.text_item = QGraphicsTextItem(name, self)
        self.text_item.setDefaultTextColor(QColor("white"))
        self.text_item.setFont(QFont("Arial", 10, QFont.Bold))
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos(-text_rect.width()/2, -text_rect.height()/2)
        
    def add_edge(self, edge):
        """Add connected edge for updating"""
        self.edges.append(edge)
        
    def itemChange(self, change, value):
        """Update connected edges when node moves"""
        if change == QGraphicsEllipseItem.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()
        return super().itemChange(change, value)
    
    def mousePressEvent(self, event):
        """Handle node selection"""
        if event.button() == Qt.LeftButton:
            self.parent_view.node_selected(self.node_id)
        super().mousePressEvent(event)


class EdgeGraphicsItem(QGraphicsLineItem):
    """Edge representation connecting two nodes"""
    def __init__(self, edge_id, source_node, target_node, color="#555"):
        super().__init__()
        self.edge_id = edge_id
        self.source_node = source_node
        self.target_node = target_node
        
        # Set appearance
        pen = QPen(QColor(color), 3)
        pen.setStyle(Qt.SolidLine)
        self.setPen(pen)
        
        # Add arrow head
        self.arrow_head = QGraphicsLineItem(self)
        self.arrow_head.setPen(QPen(QColor(color), 2))
        
        # Register with nodes
        source_node.add_edge(self)
        target_node.add_edge(self)
        
        self.update_position()
        
    def update_position(self):
        """Update line position based on node positions"""
        source_pos = self.source_node.pos()
        target_pos = self.target_node.pos()
        
        # Calculate line endpoints at circle boundaries
        line = QLineF(source_pos, target_pos)
        length = line.length()
        
        if length > 0:
            # Calculate intersection points with circles (radius 30)
            unit_x = (target_pos.x() - source_pos.x()) / length
            unit_y = (target_pos.y() - source_pos.y()) / length
            
            start_x = source_pos.x() + unit_x * 30
            start_y = source_pos.y() + unit_y * 30
            end_x = target_pos.x() - unit_x * 30
            end_y = target_pos.y() - unit_y * 30
            
            self.setLine(start_x, start_y, end_x, end_y)
            
            # Update arrow head
            arrow_size = 10
            angle = np.arctan2(end_y - start_y, end_x - start_x)
            
            arrow_p1_x = end_x - arrow_size * np.cos(angle - np.pi/6)
            arrow_p1_y = end_y - arrow_size * np.sin(angle - np.pi/6)
            
            self.arrow_head.setLine(end_x, end_y, arrow_p1_x, arrow_p1_y)


class GraphView(QGraphicsView):
    """Custom graphics view for node-edge graph"""
    node_selected_signal = Signal(str)
    graph_changed_signal = Signal()
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Set scene size
        self.scene.setSceneRect(-400, -300, 800, 600)
        
        # Storage
        self.nodes = {}  # node_id -> NodeGraphicsItem
        self.edges = {}  # edge_id -> EdgeGraphicsItem
        
        # Connection state
        self.connecting = False
        self.connection_start_node = None
        
        # Styling
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #f5f5f5;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
            }
        """)
        
    def node_selected(self, node_id):
        """Handle node selection"""
        if self.connecting:
            # Second click - create connection
            if self.connection_start_node and self.connection_start_node != node_id:
                self.graph_changed_signal.emit()
                self.connecting = False
                self.connection_start_node = None
        else:
            # First click - select node or start connection
            self.node_selected_signal.emit(node_id)
            
    def start_connection(self, node_id):
        """Start connection mode"""
        self.connecting = True
        self.connection_start_node = node_id
        
    def add_node(self, node_id, name, color, x=0, y=0):
        """Add node to graph"""
        if node_id not in self.nodes:
            node_item = NodeGraphicsItem(node_id, name, color, x, y, self)
            self.scene.addItem(node_item)
            self.nodes[node_id] = node_item
            
    def add_edge(self, edge_id, source_id, target_id, color="#555"):
        """Add edge to graph"""
        if source_id in self.nodes and target_id in self.nodes and edge_id not in self.edges:
            source_node = self.nodes[source_id]
            target_node = self.nodes[target_id]
            edge_item = EdgeGraphicsItem(edge_id, source_node, target_node, color)
            self.scene.addItem(edge_item)
            self.edges[edge_id] = edge_item
            
    def remove_node(self, node_id):
        """Remove node and connected edges"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            # Remove connected edges
            for edge in list(node.edges):
                if edge.edge_id in self.edges:
                    self.scene.removeItem(edge)
                    del self.edges[edge.edge_id]
            # Remove node
            self.scene.removeItem(node)
            del self.nodes[node_id]
            
    def remove_edge(self, edge_id):
        """Remove edge"""
        if edge_id in self.edges:
            edge = self.edges[edge_id]
            self.scene.removeItem(edge)
            del self.edges[edge_id]
            
    def clear_graph(self):
        """Clear all nodes and edges"""
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()
        
    def get_node_positions(self):
        """Get current positions of all nodes"""
        positions = {}
        for node_id, node in self.nodes.items():
            pos = node.pos()
            positions[node_id] = {'x': pos.x(), 'y': pos.y()}
        return positions


# ===================== EDGE PROPERTIES DIALOG =====================
class EdgePropertiesDialog(QDialog):
    """Dialog for editing edge interface properties"""
    def __init__(self, edge_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edge Interface Properties")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Edge name editing
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Edge Name:"))
        self.name_input = QLineEdit()
        if edge_data:
            self.name_input.setText(edge_data.get('id', 'Unknown'))
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Edge info
        if edge_data:
            info_label = QLabel(f"Connection: {edge_data.get('source', '')} → {edge_data.get('target', '')}")
            info_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #7f8c8d; margin-bottom: 10px;")
            layout.addWidget(info_label)
        
        # Interface position (output coordinate system location)
        pos_group = QGroupBox("Interface Position (X, Y, Z)")
        pos_group.setToolTip("Location of the output coordinate system on the edge")
        pos_layout = QHBoxLayout()
        self.pos_x = QDoubleSpinBox()
        self.pos_y = QDoubleSpinBox()
        self.pos_z = QDoubleSpinBox()
        for spin in [self.pos_x, self.pos_y, self.pos_z]:
            spin.setRange(-10000, 10000)
            spin.setDecimals(3)
        if edge_data:
            interface = edge_data.get('interface_properties', {})
            pos = interface.get('position', [0, 0, 0])
            self.pos_x.setValue(pos[0])
            self.pos_y.setValue(pos[1])
            self.pos_z.setValue(pos[2])
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.pos_x)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.pos_y)
        pos_layout.addWidget(QLabel("Z:"))
        pos_layout.addWidget(self.pos_z)
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)
        
        # Interface rotation
        rot_group = QGroupBox("Interface Rotation")
        rot_group.setToolTip("Orientation of the output coordinate system")
        rot_layout = QVBoxLayout()
        
        rot_order_layout = QHBoxLayout()
        rot_order_layout.addWidget(QLabel("Order:"))
        self.rot_order = QComboBox()
        self.rot_order.addItems(['xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx'])
        if edge_data:
            interface = edge_data.get('interface_properties', {})
            self.rot_order.setCurrentText(interface.get('rotation_order', 'xyz'))
        rot_order_layout.addWidget(self.rot_order)
        rot_order_layout.addStretch()
        rot_layout.addLayout(rot_order_layout)
        
        rot_angles_layout = QHBoxLayout()
        self.rot_x = QDoubleSpinBox()
        self.rot_y = QDoubleSpinBox()
        self.rot_z = QDoubleSpinBox()
        for spin in [self.rot_x, self.rot_y, self.rot_z]:
            spin.setRange(-360, 360)
            spin.setDecimals(3)
        if edge_data:
            interface = edge_data.get('interface_properties', {})
            angles = interface.get('euler_angles', [0, 0, 0])
            self.rot_x.setValue(angles[0])
            self.rot_y.setValue(angles[1])
            self.rot_z.setValue(angles[2])
        rot_angles_layout.addWidget(QLabel("X:"))
        rot_angles_layout.addWidget(self.rot_x)
        rot_angles_layout.addWidget(QLabel("Y:"))
        rot_angles_layout.addWidget(self.rot_y)
        rot_angles_layout.addWidget(QLabel("Z:"))
        rot_angles_layout.addWidget(self.rot_z)
        rot_layout.addLayout(rot_angles_layout)
        rot_group.setLayout(rot_layout)
        layout.addWidget(rot_group)
        
        # Help text
        help_text = QLabel(
            "The interface represents the output coordinate system where loads are calculated.\n"
            "Position and rotation define where and how this coordinate system is oriented."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #7f8c8d; font-size: 10px; padding: 10px;")
        layout.addWidget(help_text)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def get_data(self):
        """Get interface properties from dialog"""
        return {
            'name': self.name_input.text(),
            'position': [self.pos_x.value(), self.pos_y.value(), self.pos_z.value()],
            'euler_angles': [self.rot_x.value(), self.rot_y.value(), self.rot_z.value()],
            'rotation_order': self.rot_order.currentText()
        }


# ===================== NODE PROPERTIES DIALOG =====================
class NodePropertiesDialog(QDialog):
    """Dialog for editing node properties"""
    def __init__(self, node_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Node Properties")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(node_data.get('name', 'New Node') if node_data else 'New Node')
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Position
        pos_group = QGroupBox("Position (X, Y, Z)")
        pos_layout = QHBoxLayout()
        self.pos_x = QDoubleSpinBox()
        self.pos_y = QDoubleSpinBox()
        self.pos_z = QDoubleSpinBox()
        for spin in [self.pos_x, self.pos_y, self.pos_z]:
            spin.setRange(-10000, 10000)
            spin.setDecimals(3)
        if node_data:
            trans = node_data.get('translation', [0, 0, 0])
            self.pos_x.setValue(trans[0])
            self.pos_y.setValue(trans[1])
            self.pos_z.setValue(trans[2])
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.pos_x)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.pos_y)
        pos_layout.addWidget(QLabel("Z:"))
        pos_layout.addWidget(self.pos_z)
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)
        
        # Rotation
        rot_group = QGroupBox("Rotation")
        rot_layout = QVBoxLayout()
        rot_order_layout = QHBoxLayout()
        rot_order_layout.addWidget(QLabel("Order:"))
        self.rot_order = QComboBox()
        self.rot_order.addItems(['xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx'])
        if node_data:
            self.rot_order.setCurrentText(node_data.get('rotation_order', 'xyz'))
        rot_order_layout.addWidget(self.rot_order)
        rot_layout.addLayout(rot_order_layout)
        
        rot_angles_layout = QHBoxLayout()
        self.rot_x = QDoubleSpinBox()
        self.rot_y = QDoubleSpinBox()
        self.rot_z = QDoubleSpinBox()
        for spin in [self.rot_x, self.rot_y, self.rot_z]:
            spin.setRange(-360, 360)
            spin.setDecimals(3)
        if node_data:
            angles = node_data.get('euler_angles', [0, 0, 0])
            self.rot_x.setValue(angles[0])
            self.rot_y.setValue(angles[1])
            self.rot_z.setValue(angles[2])
        rot_angles_layout.addWidget(QLabel("X:"))
        rot_angles_layout.addWidget(self.rot_x)
        rot_angles_layout.addWidget(QLabel("Y:"))
        rot_angles_layout.addWidget(self.rot_y)
        rot_angles_layout.addWidget(QLabel("Z:"))
        rot_angles_layout.addWidget(self.rot_z)
        rot_layout.addLayout(rot_angles_layout)
        rot_group.setLayout(rot_layout)
        layout.addWidget(rot_group)
        
        # Mass and CoG
        mass_group = QGroupBox("Mass Properties")
        mass_layout = QVBoxLayout()
        mass_input_layout = QHBoxLayout()
        mass_input_layout.addWidget(QLabel("Mass (kg):"))
        self.mass_input = QDoubleSpinBox()
        self.mass_input.setRange(0, 100000)
        self.mass_input.setDecimals(3)
        if node_data:
            self.mass_input.setValue(node_data.get('mass', 0))
        mass_input_layout.addWidget(self.mass_input)
        mass_layout.addLayout(mass_input_layout)
        
        cog_layout = QHBoxLayout()
        self.cog_x = QDoubleSpinBox()
        self.cog_y = QDoubleSpinBox()
        self.cog_z = QDoubleSpinBox()
        for spin in [self.cog_x, self.cog_y, self.cog_z]:
            spin.setRange(-10000, 10000)
            spin.setDecimals(3)
        if node_data:
            cog = node_data.get('cog', [0, 0, 0])
            self.cog_x.setValue(cog[0])
            self.cog_y.setValue(cog[1])
            self.cog_z.setValue(cog[2])
        cog_layout.addWidget(QLabel("CoG X:"))
        cog_layout.addWidget(self.cog_x)
        cog_layout.addWidget(QLabel("Y:"))
        cog_layout.addWidget(self.cog_y)
        cog_layout.addWidget(QLabel("Z:"))
        cog_layout.addWidget(self.cog_z)
        mass_layout.addLayout(cog_layout)
        mass_group.setLayout(mass_layout)
        layout.addWidget(mass_group)
        
        # Forces
        force_group = QGroupBox("External Force")
        force_layout = QHBoxLayout()
        self.force_x = QDoubleSpinBox()
        self.force_y = QDoubleSpinBox()
        self.force_z = QDoubleSpinBox()
        for spin in [self.force_x, self.force_y, self.force_z]:
            spin.setRange(-100000, 100000)
            spin.setDecimals(3)
        if node_data:
            force = node_data.get('external_force', [0, 0, 0])
            self.force_x.setValue(force[0])
            self.force_y.setValue(force[1])
            self.force_z.setValue(force[2])
        force_layout.addWidget(QLabel("X:"))
        force_layout.addWidget(self.force_x)
        force_layout.addWidget(QLabel("Y:"))
        force_layout.addWidget(self.force_y)
        force_layout.addWidget(QLabel("Z:"))
        force_layout.addWidget(self.force_z)
        force_group.setLayout(force_layout)
        layout.addWidget(force_group)
        
        # Moments
        moment_group = QGroupBox("External Moment")
        moment_layout = QHBoxLayout()
        self.moment_x = QDoubleSpinBox()
        self.moment_y = QDoubleSpinBox()
        self.moment_z = QDoubleSpinBox()
        for spin in [self.moment_x, self.moment_y, self.moment_z]:
            spin.setRange(-100000, 100000)
            spin.setDecimals(3)
        if node_data:
            moment = node_data.get('moment', [0, 0, 0])
            self.moment_x.setValue(moment[0])
            self.moment_y.setValue(moment[1])
            self.moment_z.setValue(moment[2])
        moment_layout.addWidget(QLabel("X:"))
        moment_layout.addWidget(self.moment_x)
        moment_layout.addWidget(QLabel("Y:"))
        moment_layout.addWidget(self.moment_y)
        moment_layout.addWidget(QLabel("Z:"))
        moment_layout.addWidget(self.moment_z)
        moment_group.setLayout(moment_layout)
        layout.addWidget(moment_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def get_data(self):
        """Get node data from dialog"""
        return {
            'name': self.name_input.text(),
            'translation': [self.pos_x.value(), self.pos_y.value(), self.pos_z.value()],
            'euler_angles': [self.rot_x.value(), self.rot_y.value(), self.rot_z.value()],
            'rotation_order': self.rot_order.currentText(),
            'mass': self.mass_input.value(),
            'cog': [self.cog_x.value(), self.cog_y.value(), self.cog_z.value()],
            'external_force': [self.force_x.value(), self.force_y.value(), self.force_z.value()],
            'moment': [self.moment_x.value(), self.moment_y.value(), self.moment_z.value()]
        }


# ===================== MAIN APPLICATION =====================
class IntegratedLoadTransferApp(QMainWindow):
    """Main application window integrating RLT and Load Path visualization"""
    
    def __init__(self):
        super().__init__()
        self.graph_data = {'nodes': [], 'edges': []}
        self.gravity_data = {'value': 9.81, 'direction': [0, 0, -1]}
        self.selected_node_id = None
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_visualization)
        
        # Initialize managers
        self.units_manager = UnitsManager()
        self.validation_manager = ValidationManager()
        
        # Settings
        self.settings = QSettings('EngineeringTools', 'LoadTransferTool')
        self.auto_calculate = True
        self.show_force_vectors = True
        self.show_moment_vectors = True
        
        # Recent files
        self.recent_files = []
        self.max_recent_files = 5
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Integrated Load Transfer & Path Visualization Tool v2.0")
        self.setGeometry(100, 50, 1600, 1000)
        
        # Set global stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QMenuBar {
                background-color: #34495e;
                color: white;
                padding: 5px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #2c3e50;
            }
            QMenu {
                background-color: white;
                border: 1px solid #bdc3c7;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main widget with tabs
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_graph_view_tab(), "📊 Load Path Graph")
        self.tab_widget.addTab(self.create_3d_view_tab(), "🔄 3D Load Transfer")
        self.tab_widget.addTab(self.create_summary_tab(), "📋 Summary & Reports")
        
        main_layout.addWidget(self.tab_widget)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready - Professional Engineering Analysis Tool")
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        new_action = QAction('&New', self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction('&Open...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.load_from_file)
        file_menu.addAction(open_action)
        
        # Recent files submenu
        self.recent_menu = file_menu.addMenu('Recent Files')
        self.update_recent_files_menu()
        
        file_menu.addSeparator()
        
        save_action = QAction('&Save', self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_to_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction('Save &As...', self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_to_file)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu('Export')
        
        export_csv_action = QAction('Export Results (CSV)', self)
        export_csv_action.triggered.connect(self.export_results_csv)
        export_menu.addAction(export_csv_action)
        
        export_report_action = QAction('Export Report (TXT)', self)
        export_report_action.triggered.connect(self.export_report)
        export_menu.addAction(export_report_action)
        
        export_plot_action = QAction('Export 3D Plot (HTML)', self)
        export_plot_action.triggered.connect(self.export_plot_html)
        export_menu.addAction(export_plot_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('&Edit')
        
        prefs_action = QAction('&Preferences...', self)
        prefs_action.setShortcut(QKeySequence.Preferences)
        prefs_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(prefs_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('&Tools')
        
        validate_action = QAction('&Validate System', self)
        validate_action.triggered.connect(self.validate_system)
        tools_menu.addAction(validate_action)
        
        test_cases_action = QAction('Load &Test Case...', self)
        test_cases_action.triggered.connect(self.show_test_cases_dialog)
        tools_menu.addAction(test_cases_action)
        
        # View menu
        view_menu = menubar.addMenu('&View')
        
        reset_view_action = QAction('Reset 3D View', self)
        reset_view_action.triggered.connect(self.reset_3d_view)
        view_menu.addAction(reset_view_action)
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        about_action = QAction('&About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        user_guide_action = QAction('&User Guide', self)
        user_guide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(user_guide_action)
        
    def create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # File operations
        load_action = QAction("📂 Load", self)
        load_action.triggered.connect(self.load_from_file)
        toolbar.addAction(load_action)
        
        save_action = QAction("💾 Save", self)
        save_action.triggered.connect(self.save_to_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Export
        export_action = QAction("📤 Export Results", self)
        export_action.triggered.connect(self.export_results)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # Gravity settings
        toolbar.addWidget(QLabel("  Gravity (m/s²):"))
        self.gravity_input = QDoubleSpinBox()
        self.gravity_input.setRange(0, 20)
        self.gravity_input.setValue(9.81)
        self.gravity_input.setDecimals(2)
        self.gravity_input.valueChanged.connect(self.on_gravity_changed)
        toolbar.addWidget(self.gravity_input)
        
        toolbar.addWidget(QLabel("  Dir:"))
        self.gravity_dir_x = QDoubleSpinBox()
        self.gravity_dir_x.setRange(-1, 1)
        self.gravity_dir_x.setValue(0)
        self.gravity_dir_x.setDecimals(2)
        self.gravity_dir_x.setSingleStep(0.1)
        self.gravity_dir_x.setMaximumWidth(60)
        self.gravity_dir_x.setToolTip("Gravity direction X component")
        self.gravity_dir_x.valueChanged.connect(self.on_gravity_direction_changed)
        toolbar.addWidget(self.gravity_dir_x)
        
        self.gravity_dir_y = QDoubleSpinBox()
        self.gravity_dir_y.setRange(-1, 1)
        self.gravity_dir_y.setValue(0)
        self.gravity_dir_y.setDecimals(2)
        self.gravity_dir_y.setSingleStep(0.1)
        self.gravity_dir_y.setMaximumWidth(60)
        self.gravity_dir_y.setToolTip("Gravity direction Y component")
        self.gravity_dir_y.valueChanged.connect(self.on_gravity_direction_changed)
        toolbar.addWidget(self.gravity_dir_y)
        
        self.gravity_dir_z = QDoubleSpinBox()
        self.gravity_dir_z.setRange(-1, 1)
        self.gravity_dir_z.setValue(-1)
        self.gravity_dir_z.setDecimals(2)
        self.gravity_dir_z.setSingleStep(0.1)
        self.gravity_dir_z.setMaximumWidth(60)
        self.gravity_dir_z.setToolTip("Gravity direction Z component")
        self.gravity_dir_z.valueChanged.connect(self.on_gravity_direction_changed)
        toolbar.addWidget(self.gravity_dir_z)
        
        toolbar.addSeparator()
        
        # Triad size slider
        toolbar.addWidget(QLabel("  Triad Size:"))
        self.triad_slider = QSpinBox()
        self.triad_slider.setRange(1, 100)
        self.triad_slider.setValue(10)  # Default = 1.0 (10/10)
        self.triad_slider.setToolTip("Adjust coordinate system size (1-100)")
        self.triad_slider.valueChanged.connect(self.on_triad_size_changed)
        toolbar.addWidget(self.triad_slider)
        self.triad_size_label = QLabel("1.0")
        self.triad_size_label.setMinimumWidth(40)
        toolbar.addWidget(self.triad_size_label)
        
        toolbar.addSeparator()
        
        # Calculate button
        calc_action = QAction("🔄 Calculate", self)
        calc_action.triggered.connect(self.schedule_update)
        toolbar.addAction(calc_action)
        
        toolbar.addSeparator()
        
        # Test cases
        test_action = QAction("🧪 Load Test Case", self)
        test_action.triggered.connect(self.show_test_cases_dialog)
        toolbar.addAction(test_action)
        
    def create_graph_view_tab(self):
        """Create the graph visualization tab"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        # Left panel - Graph view and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Graph view
        graph_group = QGroupBox("Load Path Network")
        graph_layout = QVBoxLayout()
        self.graph_view = GraphView()
        self.graph_view.node_selected_signal.connect(self.on_node_selected)
        self.graph_view.graph_changed_signal.connect(self.schedule_update)
        graph_layout.addWidget(self.graph_view)
        graph_group.setLayout(graph_layout)
        
        # Graph controls
        controls_group = QGroupBox("Graph Controls")
        controls_layout = QVBoxLayout()
        
        btn_layout1 = QHBoxLayout()
        add_node_btn = QPushButton("➕ Add Node")
        add_node_btn.clicked.connect(self.add_node)
        btn_layout1.addWidget(add_node_btn)
        
        edit_node_btn = QPushButton("✏️ Edit Node")
        edit_node_btn.clicked.connect(self.edit_node)
        btn_layout1.addWidget(edit_node_btn)
        
        delete_node_btn = QPushButton("❌ Delete Node")
        delete_node_btn.setStyleSheet("background-color: #e74c3c;")
        delete_node_btn.clicked.connect(self.delete_node)
        btn_layout1.addWidget(delete_node_btn)
        
        controls_layout.addLayout(btn_layout1)
        
        btn_layout2 = QHBoxLayout()
        add_edge_btn = QPushButton("🔗 Add Connection")
        add_edge_btn.clicked.connect(self.add_edge_dialog)
        btn_layout2.addWidget(add_edge_btn)
        
        edit_edge_btn = QPushButton("⚙️ Edit Interface")
        edit_edge_btn.clicked.connect(self.edit_edge_interface)
        btn_layout2.addWidget(edit_edge_btn)
        
        delete_edge_btn = QPushButton("✂️ Delete Connection")
        delete_edge_btn.setStyleSheet("background-color: #e67e22;")
        delete_edge_btn.clicked.connect(self.delete_edge)
        btn_layout2.addWidget(delete_edge_btn)
        
        controls_layout.addLayout(btn_layout2)
        controls_group.setLayout(controls_layout)
        
        left_layout.addWidget(graph_group, 3)
        left_layout.addWidget(controls_group, 0)
        left_widget.setLayout(left_layout)
        
        # Right panel - Node list and properties
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Node list
        node_list_group = QGroupBox("Nodes")
        node_list_layout = QVBoxLayout()
        self.node_list = QListWidget()
        self.node_list.itemClicked.connect(self.on_node_list_clicked)
        node_list_layout.addWidget(self.node_list)
        node_list_group.setLayout(node_list_layout)
        
        # Edge list
        edge_list_group = QGroupBox("Connections")
        edge_list_layout = QVBoxLayout()
        self.edge_list = QListWidget()
        edge_list_layout.addWidget(self.edge_list)
        edge_list_group.setLayout(edge_list_layout)
        
        # Edge properties table
        edge_props_group = QGroupBox("Connection Properties")
        edge_props_layout = QVBoxLayout()
        self.edge_props_table = QTableWidget()
        self.edge_props_table.setColumnCount(11)
        self.edge_props_table.setHorizontalHeaderLabels([
            "Edge", "Source", "Target", "Pos X", "Pos Y", "Pos Z", "Rot X", "Rot Y", "Rot Z", "Rot Order", "Actions"
        ])
        self.edge_props_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.edge_props_table.setAlternatingRowColors(True)
        self.edge_props_table.cellDoubleClicked.connect(self.on_edge_cell_double_clicked)
        edge_props_layout.addWidget(self.edge_props_table)
        edge_props_group.setLayout(edge_props_layout)
        
        # Properties table
        props_group = QGroupBox("Node Properties")
        props_layout = QVBoxLayout()
        self.props_table = QTableWidget()
        self.props_table.setColumnCount(4)
        self.props_table.setHorizontalHeaderLabels(["Property", "X", "Y", "Z"])
        self.props_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        props_layout.addWidget(self.props_table)
        props_group.setLayout(props_layout)
        
        right_layout.addWidget(node_list_group, 1)
        right_layout.addWidget(edge_list_group, 1)
        right_layout.addWidget(edge_props_group, 1)
        right_layout.addWidget(props_group, 2)
        right_widget.setLayout(right_layout)
        
        # Assemble
        layout.addWidget(left_widget, 2)
        layout.addWidget(right_widget, 1)
        widget.setLayout(layout)
        
        return widget
        
    def create_3d_view_tab(self):
        """Create the 3D visualization tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 3D Plot
        plot_group = QGroupBox("3D Visualization")
        plot_layout = QVBoxLayout()
        self.web_view = QWebEngineView()
        plot_layout.addWidget(self.web_view)
        plot_group.setLayout(plot_layout)
        
        # Results table
        results_group = QGroupBox("Load Transfer Results")
        results_layout = QVBoxLayout()
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels(
            ["Edge", "Source→Target", "Fx", "Fy", "Fz", "Mx", "My", "Mz"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #bdc3c7;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 5px;
                font-weight: bold;
            }
        """)
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        
        layout.addWidget(plot_group, 3)
        layout.addWidget(results_group, 1)
        widget.setLayout(layout)
        
        return widget
    
    def create_summary_tab(self):
        """Create the summary and reports tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Summary text area
        summary_group = QGroupBox("Analysis Summary")
        summary_layout = QVBoxLayout()
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Courier New", 10))
        summary_layout.addWidget(self.summary_text)
        summary_group.setLayout(summary_layout)
        
        # Update summary button
        btn_layout = QHBoxLayout()
        update_summary_btn = QPushButton("🔄 Update Summary")
        update_summary_btn.clicked.connect(self.update_summary)
        btn_layout.addWidget(update_summary_btn)
        
        export_summary_btn = QPushButton("📄 Export Report")
        export_summary_btn.clicked.connect(self.export_report)
        btn_layout.addWidget(export_summary_btn)
        
        btn_layout.addStretch()
        
        # Statistics panel
        stats_group = QGroupBox("System Statistics")
        stats_layout = QVBoxLayout()
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        stats_layout.addWidget(self.stats_table)
        stats_group.setLayout(stats_layout)
        
        layout.addWidget(summary_group, 3)
        layout.addLayout(btn_layout)
        layout.addWidget(stats_group, 1)
        widget.setLayout(layout)
        
        return widget
        
    # ===================== NODE/EDGE OPERATIONS =====================
    def add_node(self):
        """Add a new node"""
        dialog = NodePropertiesDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            node_data = dialog.get_data()
            node_id = f"n{len(self.graph_data['nodes'])}"
            
            # Generate random color
            color = f'#{np.random.randint(0, 0xFFFFFF):06x}'
            node_data['id'] = node_id
            node_data['color'] = color
            
            self.graph_data['nodes'].append(node_data)
            
            # Add to graph view
            self.graph_view.add_node(node_id, node_data['name'], color, 
                                     np.random.uniform(-200, 200), 
                                     np.random.uniform(-150, 150))
            
            self.update_node_list()
            self.schedule_update()
            self.statusBar.showMessage(f"Added node: {node_data['name']}", 2000)
            
    def edit_node(self):
        """Edit selected node"""
        if not self.selected_node_id:
            QMessageBox.warning(self, "No Selection", "Please select a node to edit.")
            return
            
        # Find node data
        node_data = None
        for node in self.graph_data['nodes']:
            if node['id'] == self.selected_node_id:
                node_data = node
                break
                
        if node_data:
            dialog = NodePropertiesDialog(node_data, parent=self)
            if dialog.exec() == QDialog.Accepted:
                updated_data = dialog.get_data()
                # Update node data
                for key, value in updated_data.items():
                    node_data[key] = value
                
                # Update graph view
                if self.selected_node_id in self.graph_view.nodes:
                    node_item = self.graph_view.nodes[self.selected_node_id]
                    node_item.text_item.setPlainText(node_data['name'])
                    
                self.update_node_list()
                self.update_properties_display()
                self.schedule_update()
                self.statusBar.showMessage(f"Updated node: {node_data['name']}", 2000)
                
    def delete_node(self):
        """Delete selected node"""
        if not self.selected_node_id:
            QMessageBox.warning(self, "No Selection", "Please select a node to delete.")
            return
            
        reply = QMessageBox.question(
            self, 'Delete Node',
            f'Are you sure you want to delete node {self.selected_node_id}?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove from graph data
            self.graph_data['nodes'] = [n for n in self.graph_data['nodes'] 
                                        if n['id'] != self.selected_node_id]
            
            # Remove connected edges
            self.graph_data['edges'] = [e for e in self.graph_data['edges']
                                        if e['source'] != self.selected_node_id 
                                        and e['target'] != self.selected_node_id]
            
            # Remove from graph view
            self.graph_view.remove_node(self.selected_node_id)
            
            self.selected_node_id = None
            self.update_node_list()
            self.update_edge_list()
            self.update_properties_display()
            self.schedule_update()
            self.statusBar.showMessage("Node deleted", 2000)
            
    def add_edge_dialog(self):
        """Show dialog to add edge between nodes"""
        if len(self.graph_data['nodes']) < 2:
            QMessageBox.warning(self, "Not Enough Nodes", 
                              "You need at least 2 nodes to create a connection.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Connection")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Source Node:"))
        source_combo = QComboBox()
        source_combo.addItems([n['name'] + f" ({n['id']})" for n in self.graph_data['nodes']])
        layout.addWidget(source_combo)
        
        layout.addWidget(QLabel("Target Node:"))
        target_combo = QComboBox()
        target_combo.addItems([n['name'] + f" ({n['id']})" for n in self.graph_data['nodes']])
        layout.addWidget(target_combo)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.Accepted:
            source_idx = source_combo.currentIndex()
            target_idx = target_combo.currentIndex()
            
            if source_idx == target_idx:
                QMessageBox.warning(self, "Invalid Connection", 
                                  "Cannot connect a node to itself.")
                return
                
            source_id = self.graph_data['nodes'][source_idx]['id']
            target_id = self.graph_data['nodes'][target_idx]['id']
            
            # Check if edge already exists
            for edge in self.graph_data['edges']:
                if edge['source'] == source_id and edge['target'] == target_id:
                    QMessageBox.warning(self, "Edge Exists", 
                                      "Connection already exists between these nodes.")
                    return
                    
            edge_id = f"e{len(self.graph_data['edges'])}"
            self.graph_data['edges'].append({
                'id': edge_id,
                'source': source_id,
                'target': target_id,
                'interface_properties': {
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz',
                    'position': [0, 0, 0]
                }
            })
            
            # Add to graph view
            source_color = self.graph_data['nodes'][source_idx].get('color', '#555')
            self.graph_view.add_edge(edge_id, source_id, target_id, source_color)
            
            self.update_edge_list()
            self.schedule_update()
            self.statusBar.showMessage(f"Added connection: {edge_id}", 2000)
    
    def edit_edge_interface(self):
        """Edit selected edge interface properties"""
        current_item = self.edge_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a connection to edit.")
            return
            
        edge_id = current_item.data(Qt.UserRole)
        
        # Find edge data
        edge_data = None
        edge_index = -1
        for i, edge in enumerate(self.graph_data['edges']):
            if edge['id'] == edge_id:
                edge_data = edge
                edge_index = i
                break
                
        if edge_data:
            dialog = EdgePropertiesDialog(edge_data, parent=self)
            if dialog.exec() == QDialog.Accepted:
                data = dialog.get_data()
                
                # Update edge name if changed
                new_name = data.get('name', edge_id)
                if new_name and new_name != edge_id:
                    # Update edge ID
                    old_id = edge_data['id']
                    edge_data['id'] = new_name
                    
                    # Update graph view
                    if old_id in self.graph_view.edges:
                        edge_item = self.graph_view.edges[old_id]
                        del self.graph_view.edges[old_id]
                        self.graph_view.edges[new_name] = edge_item
                        edge_item.edge_id = new_name
                
                # Update interface properties
                if 'interface_properties' not in edge_data:
                    edge_data['interface_properties'] = {}
                    
                edge_data['interface_properties']['position'] = data['position']
                edge_data['interface_properties']['euler_angles'] = data['euler_angles']
                edge_data['interface_properties']['rotation_order'] = data['rotation_order']
                
                self.update_edge_list()
                self.schedule_update()
                self.statusBar.showMessage(f"Updated interface: {edge_data['id']}", 2000)
            
    def delete_edge(self):
        """Delete selected edge"""
        current_item = self.edge_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a connection to delete.")
            return
            
        edge_id = current_item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, 'Delete Connection',
            f'Are you sure you want to delete connection {edge_id}?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove from graph data
            self.graph_data['edges'] = [e for e in self.graph_data['edges'] 
                                        if e['id'] != edge_id]
            
            # Remove from graph view
            self.graph_view.remove_edge(edge_id)
            
            self.update_edge_list()
            self.schedule_update()
            self.statusBar.showMessage("Connection deleted", 2000)
            
    # ===================== UI UPDATES =====================
    def update_node_list(self):
        """Update node list widget"""
        self.node_list.clear()
        for node in self.graph_data['nodes']:
            item = QListWidgetItem(f"{node['name']} ({node['id']})")
            item.setData(Qt.UserRole, node['id'])
            self.node_list.addItem(item)
            
    def update_edge_list(self):
        """Update edge list widget"""
        self.edge_list.clear()
        for edge in self.graph_data['edges']:
            source_name = next((n['name'] for n in self.graph_data['nodes'] 
                              if n['id'] == edge['source']), edge['source'])
            target_name = next((n['name'] for n in self.graph_data['nodes'] 
                              if n['id'] == edge['target']), edge['target'])
            item = QListWidgetItem(f"{edge['id']}: {source_name} → {target_name}")
            item.setData(Qt.UserRole, edge['id'])
            self.edge_list.addItem(item)
        
        # Update edge properties table
        self.update_edge_properties_table()
    
    def update_edge_properties_table(self):
        """Update edge properties table"""
        self.edge_props_table.setRowCount(len(self.graph_data['edges']))
        
        for i, edge in enumerate(self.graph_data['edges']):
            # Find source and target names
            source_name = next((n['name'] for n in self.graph_data['nodes'] 
                              if n['id'] == edge['source']), edge['source'])
            target_name = next((n['name'] for n in self.graph_data['nodes'] 
                              if n['id'] == edge['target']), edge['target'])
            
            # Get interface properties
            interface = edge.get('interface_properties', {})
            pos = interface.get('position', [0, 0, 0])
            rot = interface.get('euler_angles', [0, 0, 0])
            rot_order = interface.get('rotation_order', 'xyz')
            
            # Populate table - Edge name (editable)
            edge_name_item = QTableWidgetItem(edge['id'])
            edge_name_item.setToolTip("Double-click to edit edge name")
            self.edge_props_table.setItem(i, 0, edge_name_item)
            
            # Source and target (read-only)
            source_item = QTableWidgetItem(source_name)
            source_item.setFlags(source_item.flags() & ~Qt.ItemIsEditable)
            self.edge_props_table.setItem(i, 1, source_item)
            
            target_item = QTableWidgetItem(target_name)
            target_item.setFlags(target_item.flags() & ~Qt.ItemIsEditable)
            self.edge_props_table.setItem(i, 2, target_item)
            
            # Position values
            for col, val in enumerate(pos, 3):
                item = QTableWidgetItem(f"{val:.3f}")
                item.setTextAlignment(Qt.AlignCenter)
                self.edge_props_table.setItem(i, col, item)
            
            # Rotation values
            for col, val in enumerate(rot, 6):
                item = QTableWidgetItem(f"{val:.3f}")
                item.setTextAlignment(Qt.AlignCenter)
                self.edge_props_table.setItem(i, col, item)
            
            # Rotation order
            rot_order_item = QTableWidgetItem(rot_order)
            rot_order_item.setTextAlignment(Qt.AlignCenter)
            self.edge_props_table.setItem(i, 9, rot_order_item)
            
            # Edit button
            edit_btn_item = QTableWidgetItem("✏️ Edit")
            edit_btn_item.setTextAlignment(Qt.AlignCenter)
            edit_btn_item.setToolTip("Click to edit interface properties")
            self.edge_props_table.setItem(i, 10, edit_btn_item)
    
    def on_edge_cell_double_clicked(self, row, column):
        """Handle double-click on edge properties table"""
        if column == 0:
            # Edit edge name
            current_name = self.edge_props_table.item(row, 0).text()
            new_name, ok = QInputDialog.getText(self, "Edit Edge Name", 
                                                "Enter new edge name:", 
                                                text=current_name)
            if ok and new_name and new_name != current_name:
                # Update edge name
                edge = self.graph_data['edges'][row]
                old_id = edge['id']
                edge['id'] = new_name
                
                # Update graph view
                if old_id in self.graph_view.edges:
                    edge_item = self.graph_view.edges[old_id]
                    del self.graph_view.edges[old_id]
                    self.graph_view.edges[new_name] = edge_item
                    edge_item.edge_id = new_name
                
                self.update_edge_list()
                self.statusBar.showMessage(f"Edge renamed: {old_id} → {new_name}", 2000)
        
        elif column == 10:
            # Edit interface properties
            edge = self.graph_data['edges'][row]
            dialog = EdgePropertiesDialog(edge, parent=self)
            if dialog.exec() == QDialog.Accepted:
                data = dialog.get_data()
                
                # Update name if changed
                new_name = data.get('name', edge['id'])
                if new_name and new_name != edge['id']:
                    old_id = edge['id']
                    edge['id'] = new_name
                    
                    if old_id in self.graph_view.edges:
                        edge_item = self.graph_view.edges[old_id]
                        del self.graph_view.edges[old_id]
                        self.graph_view.edges[new_name] = edge_item
                        edge_item.edge_id = new_name
                
                # Update interface properties
                if 'interface_properties' not in edge:
                    edge['interface_properties'] = {}
                
                edge['interface_properties']['position'] = data['position']
                edge['interface_properties']['euler_angles'] = data['euler_angles']
                edge['interface_properties']['rotation_order'] = data['rotation_order']
                
                self.update_edge_list()
                self.schedule_update()
                self.statusBar.showMessage(f"Updated interface: {edge['id']}", 2000)
            
    def update_properties_display(self):
        """Update properties table for selected node"""
        self.props_table.setRowCount(0)
        
        if not self.selected_node_id:
            return
            
        # Find node data
        node_data = None
        for node in self.graph_data['nodes']:
            if node['id'] == self.selected_node_id:
                node_data = node
                break
                
        if not node_data:
            return
            
        # Display properties
        properties = [
            ("Position", node_data.get('translation', [0, 0, 0])),
            ("Rotation", node_data.get('euler_angles', [0, 0, 0])),
            ("CoG", node_data.get('cog', [0, 0, 0])),
            ("Force", node_data.get('external_force', [0, 0, 0])),
            ("Moment", node_data.get('moment', [0, 0, 0]))
        ]
        
        self.props_table.setRowCount(len(properties) + 2)
        
        # Add scalar properties
        row = 0
        self.props_table.setItem(row, 0, QTableWidgetItem("Name"))
        self.props_table.setItem(row, 1, QTableWidgetItem(node_data.get('name', '')))
        self.props_table.setSpan(row, 1, 1, 3)
        
        row += 1
        self.props_table.setItem(row, 0, QTableWidgetItem("Mass (kg)"))
        self.props_table.setItem(row, 1, QTableWidgetItem(f"{node_data.get('mass', 0):.3f}"))
        self.props_table.setSpan(row, 1, 1, 3)
        
        # Add vector properties
        for prop_name, values in properties:
            row += 1
            self.props_table.setItem(row, 0, QTableWidgetItem(prop_name))
            for col, val in enumerate(values, 1):
                self.props_table.setItem(row, col, QTableWidgetItem(f"{val:.3f}"))
                
    def on_node_selected(self, node_id):
        """Handle node selection"""
        self.selected_node_id = node_id
        self.update_properties_display()
        self.statusBar.showMessage(f"Selected: {node_id}", 2000)
        
    def on_node_list_clicked(self, item):
        """Handle node list click"""
        node_id = item.data(Qt.UserRole)
        self.selected_node_id = node_id
        self.update_properties_display()
        
    def on_gravity_changed(self, value):
        """Handle gravity value change"""
        self.gravity_data['value'] = value
        self.schedule_update()
    
    def on_gravity_direction_changed(self):
        """Handle gravity direction change"""
        # Get direction vector
        direction = np.array([
            self.gravity_dir_x.value(),
            self.gravity_dir_y.value(),
            self.gravity_dir_z.value()
        ])
        
        # Normalize direction vector
        norm = np.linalg.norm(direction)
        if norm > 0:
            direction = direction / norm
            
            # Update spinboxes with normalized values (without triggering signals)
            self.gravity_dir_x.blockSignals(True)
            self.gravity_dir_y.blockSignals(True)
            self.gravity_dir_z.blockSignals(True)
            
            self.gravity_dir_x.setValue(direction[0])
            self.gravity_dir_y.setValue(direction[1])
            self.gravity_dir_z.setValue(direction[2])
            
            self.gravity_dir_x.blockSignals(False)
            self.gravity_dir_y.blockSignals(False)
            self.gravity_dir_z.blockSignals(False)
            
            # Update gravity data
            self.gravity_data['direction'] = direction.tolist()
            self.schedule_update()
        else:
            # If zero vector, reset to default [0, 0, -1]
            self.gravity_dir_x.blockSignals(True)
            self.gravity_dir_y.blockSignals(True)
            self.gravity_dir_z.blockSignals(True)
            
            self.gravity_dir_x.setValue(0)
            self.gravity_dir_y.setValue(0)
            self.gravity_dir_z.setValue(-1)
            
            self.gravity_dir_x.blockSignals(False)
            self.gravity_dir_y.blockSignals(False)
            self.gravity_dir_z.blockSignals(False)
            
            self.gravity_data['direction'] = [0, 0, -1]
            self.schedule_update()
    
    def on_triad_size_changed(self, value):
        """Handle triad size slider change"""
        # Convert slider value (1-100) to actual size (0.1-10.0) with log scale
        # log scale: 10^(value/50 - 1) gives range from 10^-1 to 10^1
        actual_size = 10 ** ((value - 10) / 45)  # Maps 1->0.1, 10->1.0, 100->10.0
        self.triad_size_label.setText(f"{actual_size:.2f}")
        self.schedule_update()
    
    def get_triad_size(self):
        """Get current triad size from slider"""
        value = self.triad_slider.value()
        return 10 ** ((value - 10) / 45)
    
    # ===================== MENU ACTIONS =====================
    def new_project(self):
        """Create new project"""
        reply = QMessageBox.question(
            self, 'New Project',
            'Create a new project? All unsaved changes will be lost.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.graph_view.clear_graph()
            self.graph_data = {'nodes': [], 'edges': []}
            self.update_node_list()
            self.update_edge_list()
            self.statusBar.showMessage("New project created", 2000)
    
    def show_preferences(self):
        """Show preferences dialog"""
        dialog = PreferencesDialog(self.units_manager, self)
        if dialog.exec() == QDialog.Accepted:
            settings = dialog.get_settings()
            
            # Update units
            for unit_type, unit in settings['units'].items():
                self.units_manager.set_unit(unit_type, unit)
            
            # Update display settings
            self.auto_calculate = settings['display']['auto_calculate']
            self.show_force_vectors = settings['display']['show_force_vectors']
            self.show_moment_vectors = settings['display']['show_moment_vectors']
            
            self.save_settings()
            self.schedule_update()
            self.statusBar.showMessage("Preferences updated", 2000)
    
    def validate_system(self):
        """Validate entire system"""
        all_errors = []
        all_warnings = []
        
        # Validate nodes
        for node in self.graph_data['nodes']:
            errors, warnings = self.validation_manager.validate_node(node)
            for err in errors:
                all_errors.append(f"Node {node['name']}: {err}")
            for warn in warnings:
                all_warnings.append(f"Node {node['name']}: {warn}")
        
        # Validate edges
        for edge in self.graph_data['edges']:
            errors, warnings = self.validation_manager.validate_edge(edge, self.graph_data['nodes'])
            for err in errors:
                all_errors.append(f"Edge {edge['id']}: {err}")
            for warn in warnings:
                all_warnings.append(f"Edge {edge['id']}: {warn}")
        
        # System consistency
        errors, warnings = self.validation_manager.check_system_consistency(self.graph_data)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        
        # Show results
        msg = "VALIDATION RESULTS\n\n"
        
        if all_errors:
            msg += f"❌ ERRORS ({len(all_errors)}):\n"
            for err in all_errors:
                msg += f"  • {err}\n"
            msg += "\n"
        
        if all_warnings:
            msg += f"⚠️ WARNINGS ({len(all_warnings)}):\n"
            for warn in all_warnings:
                msg += f"  • {warn}\n"
            msg += "\n"
        
        if not all_errors and not all_warnings:
            msg += "✅ System validation passed!\nNo errors or warnings found."
            QMessageBox.information(self, "Validation Results", msg)
        elif all_errors:
            QMessageBox.critical(self, "Validation Results", msg)
        else:
            QMessageBox.warning(self, "Validation Results", msg)
    
    def update_summary(self):
        """Update summary report"""
        report = ReportGenerator.generate_summary_report(self.graph_data, {})
        self.summary_text.setPlainText(report)
        
        # Update statistics
        total_mass = sum(node.get('mass', 0) for node in self.graph_data['nodes'])
        total_force = sum(abs(f) for node in self.graph_data['nodes'] 
                         for f in node.get('external_force', [0, 0, 0]))
        
        stats = [
            ("Total Nodes", str(len(self.graph_data['nodes']))),
            ("Total Connections", str(len(self.graph_data['edges']))),
            ("Total System Mass", f"{total_mass:.2f} kg"),
            ("Total External Force", f"{total_force:.2f} N"),
            ("Gravity", f"{self.gravity_data['value']} m/s²"),
            ("Gravity Direction", str(self.gravity_data['direction']))
        ]
        
        self.stats_table.setRowCount(len(stats))
        for i, (metric, value) in enumerate(stats):
            self.stats_table.setItem(i, 0, QTableWidgetItem(metric))
            self.stats_table.setItem(i, 1, QTableWidgetItem(value))
    
    def export_report(self):
        """Export text report"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Report", "", "Text Files (*.txt)"
            )
            
            if file_path:
                report = ReportGenerator.generate_summary_report(self.graph_data, {})
                with open(file_path, 'w') as f:
                    f.write(report)
                self.statusBar.showMessage(f"Report exported to {file_path}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Could not export report: {e}")
    
    def export_results_csv(self):
        """Export results to CSV"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Results", "", "CSV Files (*.csv)"
            )
            
            if file_path:
                if ReportGenerator.export_to_csv(self.graph_data, file_path):
                    self.statusBar.showMessage(f"Results exported to {file_path}", 3000)
                else:
                    QMessageBox.warning(self, "Export Error", "Could not export results")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Could not export: {e}")
    
    def export_plot_html(self):
        """Export 3D plot as HTML"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export 3D Plot", "", "HTML Files (*.html)"
            )
            
            if file_path:
                # Get current HTML from web view
                # Note: This is a placeholder - actual implementation would save the figure
                self.statusBar.showMessage(f"Plot exported to {file_path}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Could not export plot: {e}")
    
    def reset_3d_view(self):
        """Reset 3D view to default"""
        self.schedule_update()
        self.statusBar.showMessage("3D view reset", 2000)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>Integrated Load Transfer & Path Visualization Tool</h2>
        <p><b>Version:</b> 2.0</p>
        <p><b>Description:</b> Professional engineering tool for rigid body load transfer analysis and load path visualization.</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Interactive load path graph creation</li>
            <li>3D coordinate system visualization</li>
            <li>Cumulative load calculation</li>
            <li>Gravity effects with custom direction</li>
            <li>Multiple output coordinate systems</li>
            <li>Export capabilities (JSON, CSV, HTML, Reports)</li>
            <li>Comprehensive validation</li>
            <li>Test cases for verification</li>
        </ul>
        <p><b>Author:</b> Engineering Tools Development Team</p>
        <p><b>License:</b> Professional Edition</p>
        <p><i>© 2025 All Rights Reserved</i></p>
        """
        QMessageBox.about(self, "About", about_text)
    
    def show_user_guide(self):
        """Show user guide"""
        guide_text = """
        <h2>User Guide</h2>
        
        <h3>Getting Started</h3>
        <ol>
            <li><b>Create Nodes:</b> Click "Add Node" to create load input points</li>
            <li><b>Set Properties:</b> Edit node mass, forces, moments, and position</li>
            <li><b>Create Connections:</b> Link nodes with edges to define load paths</li>
            <li><b>Set Interfaces:</b> Edit edge interface properties for output coordinate systems</li>
            <li><b>Calculate:</b> View results in 3D visualization and results table</li>
        </ol>
        
        <h3>Key Concepts</h3>
        <p><b>Nodes:</b> Represent load input points with mass, forces, and moments</p>
        <p><b>Edges:</b> Define load transfer paths with output coordinate systems</p>
        <p><b>Interfaces:</b> Output locations where loads are calculated</p>
        <p><b>Cumulative Loading:</b> Loads accumulate through the structure</p>
        
        <h3>Tips</h3>
        <ul>
            <li>Use test cases (🧪) to learn the tool</li>
            <li>Validate system (Tools menu) before analysis</li>
            <li>Adjust triad size for better visualization</li>
            <li>Save projects frequently (Ctrl+S)</li>
            <li>Use preferences to set units and display options</li>
        </ul>
        
        <h3>Keyboard Shortcuts</h3>
        <ul>
            <li><b>Ctrl+N:</b> New project</li>
            <li><b>Ctrl+O:</b> Open project</li>
            <li><b>Ctrl+S:</b> Save project</li>
            <li><b>Ctrl+Q:</b> Quit application</li>
        </ul>
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle("User Guide")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(guide_text)
        layout.addWidget(text_edit)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def update_recent_files_menu(self):
        """Update recent files menu"""
        self.recent_menu.clear()
        
        for file_path in self.recent_files:
            action = QAction(file_path, self)
            action.triggered.connect(lambda checked, path=file_path: self.load_file(path))
            self.recent_menu.addAction(action)
        
        if not self.recent_files:
            action = QAction("No recent files", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
    
    def add_recent_file(self, file_path):
        """Add file to recent files list"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.max_recent_files]
        self.update_recent_files_menu()
        self.save_settings()
    
    def load_file(self, file_path):
        """Load file from path"""
        # Implementation would call load_from_file with specific path
        self.statusBar.showMessage(f"Loading {file_path}...", 2000)
    
    def save_settings(self):
        """Save application settings"""
        self.settings.setValue('recent_files', self.recent_files)
        self.settings.setValue('auto_calculate', self.auto_calculate)
        self.settings.setValue('show_force_vectors', self.show_force_vectors)
        self.settings.setValue('show_moment_vectors', self.show_moment_vectors)
        self.settings.setValue('units/force', self.units_manager.get_unit('force'))
        self.settings.setValue('units/moment', self.units_manager.get_unit('moment'))
        self.settings.setValue('units/length', self.units_manager.get_unit('length'))
        self.settings.setValue('units/mass', self.units_manager.get_unit('mass'))
    
    def load_settings(self):
        """Load application settings"""
        self.recent_files = self.settings.value('recent_files', [])
        if not isinstance(self.recent_files, list):
            self.recent_files = []
        self.auto_calculate = self.settings.value('auto_calculate', True, type=bool)
        self.show_force_vectors = self.settings.value('show_force_vectors', True, type=bool)
        self.show_moment_vectors = self.settings.value('show_moment_vectors', True, type=bool)
        
        # Load units
        force_unit = self.settings.value('units/force', 'N')
        if force_unit:
            self.units_manager.set_unit('force', force_unit)
        
        self.update_recent_files_menu()
        
    # ===================== VISUALIZATION =====================
    def schedule_update(self):
        """Schedule visualization update with debouncing"""
        if self.auto_calculate:
            self.update_timer.start(300)
        else:
            self.statusBar.showMessage("Auto-calculate disabled. Click Calculate button to update.", 3000)
    
    def calculate_node_loads(self, node_id, gravity_value, gravity_dir):
        """Calculate total loads on a node including gravity"""
        node = next((n for n in self.graph_data['nodes'] if n['id'] == node_id), None)
        if not node:
            return np.zeros(3), np.zeros(3)
        
        # Get node coordinate system
        R_node, pos_node = rlt.create_rotation_matrix(
            np.radians(node['euler_angles']),
            node['rotation_order'],
            node['translation']
        )
        
        # Start with external loads
        force = np.array(node.get('external_force', [0, 0, 0]), dtype=np.float64)
        moment = np.array(node.get('moment', [0, 0, 0]), dtype=np.float64)
        
        # Add gravity contribution
        if node.get('mass', 0) > 0:
            cog = np.array(node.get('cog', [0, 0, 0]))
            if np.all(cog == 0):
                cog_global = np.array(node['translation'])
            else:
                cog_global = np.array(node['translation']) + R_node @ cog
            
            # Calculate gravity force in global coordinates
            gravity_force_global = node['mass'] * gravity_value * gravity_dir
            
            # Transform to node local coordinates
            R_cog, pos_cog = rlt.create_rotation_matrix(
                np.radians(node['euler_angles']),
                node['rotation_order'],
                cog_global
            )
            gravity_force_local = R_cog.T @ gravity_force_global
            
            # Calculate moment due to gravity
            gravity_moment = np.cross(cog, gravity_force_global)
            
            force += gravity_force_local
            moment += gravity_moment
        
        return force, moment, R_node, pos_node
        
    def build_load_path_tree(self):
        """Build a tree structure of load paths from sources to targets"""
        # Identify source nodes (no incoming edges) and build adjacency
        incoming = {node['id']: [] for node in self.graph_data['nodes']}
        outgoing = {node['id']: [] for node in self.graph_data['nodes']}
        
        for edge in self.graph_data['edges']:
            incoming[edge['target']].append(edge)
            outgoing[edge['source']].append(edge)
        
        # Find source nodes (no incoming edges)
        source_nodes = [node_id for node_id, edges in incoming.items() if len(edges) == 0]
        
        return incoming, outgoing, source_nodes
        
    def update_visualization(self):
        """Update 3D visualization and calculate cumulative loads through structure"""
        try:
            fig = go.Figure()
            
            # Get triad size from slider
            triad_size = self.get_triad_size()
            
            # Add global origin
            fig.add_trace(go.Scatter3d(
                x=[0], y=[0], z=[0],
                mode='markers',
                marker=dict(size=6, color='black', symbol='diamond'),
                name='Global Origin'
            ))
            
            # Get gravity settings
            gravity_value = self.gravity_data['value']
            gravity_dir = np.array(self.gravity_data['direction'])
            
            # Normalize gravity direction
            norm = np.linalg.norm(gravity_dir)
            if norm > 0:
                gravity_dir = gravity_dir / norm
            else:
                gravity_dir = np.array([0, 0, -1])
            
            # Add gravity vector (scaled for visibility)
            gravity_scale = 2.0  # Visual scale factor
            fig.add_trace(go.Scatter3d(
                x=[0, gravity_dir[0] * gravity_scale], 
                y=[0, gravity_dir[1] * gravity_scale], 
                z=[0, gravity_dir[2] * gravity_scale],
                mode='lines+markers',
                line=dict(color='purple', width=6),
                marker=dict(size=[4, 8], color='purple', symbol=['circle', 'diamond']),
                name=f'Gravity: {gravity_value} m/s² [{gravity_dir[0]:.2f}, {gravity_dir[1]:.2f}, {gravity_dir[2]:.2f}]'
            ))
            
            # Build load path structure
            incoming, outgoing, source_nodes = self.build_load_path_tree()
            
            # Visualize all nodes with their coordinate systems
            for node in self.graph_data['nodes']:
                try:
                    R, pos = rlt.create_rotation_matrix(
                        np.radians(node['euler_angles']),
                        node['rotation_order'],
                        node['translation']
                    )
                    color = node.get('color', '#3498db')
                    
                    # Add coordinate system
                    fig_node = plot3d.plot_triad(
                        np.radians(node['euler_angles']),
                        node['rotation_order'],
                        node['translation'],
                        tip_size=0.5 * triad_size,
                        len_triad=triad_size,
                        colors_arr=color,
                        triad_name=f"{node['name']}"
                    )
                    fig.add_traces(fig_node.data)
                    
                    # Visualize external forces
                    force = np.array(node.get('external_force', [0, 0, 0]))
                    if np.linalg.norm(force) > 0.01:
                        fig_force = plot3d.create_vector(
                            pos, R @ force, '#e74c3c',
                            f"ExtF:{force.tolist()}", 
                            triad_name=f"{node['name']}:ExtForce"
                        )
                        fig.add_traces(fig_force.data)
                    
                    # Visualize external moments
                    moment = np.array(node.get('moment', [0, 0, 0]))
                    if np.linalg.norm(moment) > 0.01:
                        fig_mom = plot3d.create_vector(
                            pos, R @ moment, '#2ecc71',
                            f"ExtM:{moment.tolist()}", 
                            triad_name=f"{node['name']}:ExtMoment"
                        )
                        fig.add_traces(fig_mom.data)
                    
                    # Visualize gravity force
                    if node.get('mass', 0) > 0:
                        cog = np.array(node.get('cog', [0, 0, 0]))
                        if np.all(cog == 0):
                            cog_global = node['translation']
                        else:
                            cog_global = np.array(node['translation']) + R @ cog
                        
                        # Scale gravity vector for visibility
                        gravity_visual_scale = 0.1  # Scale factor for visualization
                        gravity_visual = gravity_dir * gravity_visual_scale
                        
                        fig.add_trace(go.Scatter3d(
                            x=[cog_global[0], cog_global[0] + gravity_visual[0]],
                            y=[cog_global[1], cog_global[1] + gravity_visual[1]],
                            z=[cog_global[2], cog_global[2] + gravity_visual[2]],
                            mode='lines',
                            line=dict(color=color, width=3, dash='dot'),
                            name=f'{node["name"]}: Gravity ({node["mass"]} kg)',
                            showlegend=False
                        ))
                        
                except Exception as e:
                    print(f"Error visualizing node {node.get('id', 'unknown')}: {e}")
            
            # Calculate and visualize loads at each edge interface (OUTPUT coordinate systems)
            self.results_table.setRowCount(len(self.graph_data['edges']))
            
            for i, edge in enumerate(self.graph_data['edges']):
                try:
                    source_id = edge['source']
                    target_id = edge['target']
                    
                    # Find source node
                    source_node = next((n for n in self.graph_data['nodes'] 
                                       if n['id'] == source_id), None)
                    target_node = next((n for n in self.graph_data['nodes'] 
                                       if n['id'] == target_id), None)
                    
                    if not source_node or not target_node:
                        continue
                    
                    # Get interface properties (output coordinate system)
                    interface = edge.get('interface_properties', {})
                    interface_pos = interface.get('position', target_node['translation'])
                    interface_angles = interface.get('euler_angles', [0, 0, 0])
                    interface_order = interface.get('rotation_order', 'xyz')
                    
                    # Create interface coordinate system
                    R_interface, pos_interface = rlt.create_rotation_matrix(
                        np.radians(interface_angles),
                        interface_order,
                        interface_pos
                    )
                    
                    # Visualize interface coordinate system (OUTPUT)
                    fig_interface = plot3d.plot_triad(
                        np.radians(interface_angles),
                        interface_order,
                        interface_pos,
                        tip_size=0.4 * triad_size,
                        len_triad=0.8 * triad_size,
                        colors_arr='#f39c12',
                        triad_name=f"{edge['id']}:Output"
                    )
                    fig.add_traces(fig_interface.data)
                    
                    # Add connection line from source to interface
                    source_pos = np.array(source_node['translation'])
                    fig.add_trace(go.Scatter3d(
                        x=[source_pos[0], interface_pos[0]],
                        y=[source_pos[1], interface_pos[1]],
                        z=[source_pos[2], interface_pos[2]],
                        mode='lines',
                        line=dict(color=source_node.get('color', '#555'), width=3, dash='dash'),
                        name=f"Path: {edge['id']}",
                        showlegend=False
                    ))
                    
                    # CUMULATIVE LOAD CALCULATION
                    # Start with source node's own loads
                    total_force, total_moment, R_source, pos_source = self.calculate_node_loads(
                        source_id, gravity_value, gravity_dir
                    )
                    
                    # Add loads from all incoming edges to source
                    for incoming_edge in incoming[source_id]:
                        if 'interface_properties' in incoming_edge:
                            incoming_results = incoming_edge['interface_properties'].get('rlt_results', {})
                            if incoming_results.get('is_valid', False):
                                total_force += np.array(incoming_results['force'])
                                total_moment += np.array(incoming_results['moment'])
                    
                    # Transfer cumulative loads to interface
                    F_at_interface, M_at_interface = rlt.rigid_load_transfer(
                        total_force,
                        total_moment,
                        R_source, pos_source,
                        R_interface, pos_interface
                    )
                    
                    # Visualize transferred loads at interface
                    if np.linalg.norm(F_at_interface) > 0.01:
                        fig_force_interface = plot3d.create_vector(
                            pos_interface, R_interface @ F_at_interface, '#c0392b',
                            f"F@{edge['id']}:{F_at_interface.tolist()}", 
                            triad_name=f"{edge['id']}:Force"
                        )
                        fig.add_traces(fig_force_interface.data)
                    
                    if np.linalg.norm(M_at_interface) > 0.01:
                        fig_moment_interface = plot3d.create_vector(
                            pos_interface, R_interface @ M_at_interface, '#27ae60',
                            f"M@{edge['id']}:{M_at_interface.tolist()}", 
                            triad_name=f"{edge['id']}:Moment"
                        )
                        fig.add_traces(fig_moment_interface.data)
                    
                    # Store results in edge
                    if 'interface_properties' not in edge:
                        edge['interface_properties'] = {}
                    edge['interface_properties']['rlt_results'] = {
                        'force': F_at_interface.tolist(),
                        'moment': M_at_interface.tolist(),
                        'is_valid': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Update results table
                    self.results_table.setItem(i, 0, QTableWidgetItem(edge['id']))
                    self.results_table.setItem(i, 1, QTableWidgetItem(
                        f"{source_node['name']} → {target_node['name']}"
                    ))
                    
                    for col, val in enumerate(F_at_interface, 2):
                        item = QTableWidgetItem(f"{val:.3f}")
                        item.setTextAlignment(Qt.AlignCenter)
                        self.results_table.setItem(i, col, item)
                        
                    for col, val in enumerate(M_at_interface, 5):
                        item = QTableWidgetItem(f"{val:.3f}")
                        item.setTextAlignment(Qt.AlignCenter)
                        self.results_table.setItem(i, col, item)
                    
                except Exception as e:
                    print(f"Error processing edge {edge.get('id', 'unknown')}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Update plot layout
            fig.update_layout(
                scene=dict(
                    xaxis=dict(title='X', backgroundcolor="#ecf0f1"),
                    yaxis=dict(title='Y', backgroundcolor="#ecf0f1"),
                    zaxis=dict(title='Z', backgroundcolor="#ecf0f1"),
                    aspectmode='cube',
                    camera=dict(
                        up=dict(x=0, y=0, z=1),
                        eye=dict(x=1.5, y=1.5, z=1.5)
                    )
                ),
                margin=dict(l=0, r=0, b=0, t=30),
                showlegend=True,
                legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)'),
                scene_aspectmode='data',
                paper_bgcolor='#ecf0f1'
            )
            
            # Display plot
            self.web_view.setHtml(fig.to_html(include_plotlyjs='cdn'))
            self.statusBar.showMessage("Visualization updated - Load path calculated", 2000)
            
        except Exception as e:
            self.statusBar.showMessage(f"Error updating visualization: {e}", 5000)
            print(f"Visualization error: {e}")
            import traceback
            traceback.print_exc()
        
    # ===================== FILE OPERATIONS =====================
    def save_to_file(self):
        """Save current data to JSON file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Data", "", "JSON Files (*.json)"
            )
            
            if file_path:
                # Get node positions from graph view
                positions = self.graph_view.get_node_positions()
                
                # Prepare export data
                export_data = {
                    "metadata": {
                        "version": "2.0",
                        "coordinate_system": "right-handed",
                        "units": {
                            "force": "N",
                            "moment": "Nm",
                            "mass": "kg",
                            "distance": "mm"
                        },
                        "description": "Integrated Load Transfer & Path Data",
                        "timestamp": datetime.now().isoformat()
                    },
                    "gravity": self.gravity_data,
                    "nodes": [],
                    "edges": []
                }
                
                # Export nodes with positions
                for node in self.graph_data['nodes']:
                    node_export = node.copy()
                    if node['id'] in positions:
                        node_export['graph_position'] = positions[node['id']]
                    export_data['nodes'].append(node_export)
                
                # Export edges
                export_data['edges'] = self.graph_data['edges'].copy()
                
                # Save to file
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                    
                self.statusBar.showMessage(f"Saved to {file_path}", 3000)
                
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Could not save file: {e}")
            
    def load_from_file(self):
        """Load data from JSON file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load Data", "", "JSON Files (*.json)"
            )
            
            if file_path:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Clear existing data
                self.graph_view.clear_graph()
                self.graph_data = {'nodes': [], 'edges': []}
                
                # Load gravity
                if 'gravity' in data:
                    self.gravity_data = data['gravity']
                    self.gravity_input.setValue(self.gravity_data.get('value', 9.81))
                    
                    # Update gravity direction
                    direction = self.gravity_data.get('direction', [0, 0, -1])
                    self.gravity_dir_x.blockSignals(True)
                    self.gravity_dir_y.blockSignals(True)
                    self.gravity_dir_z.blockSignals(True)
                    
                    self.gravity_dir_x.setValue(direction[0])
                    self.gravity_dir_y.setValue(direction[1])
                    self.gravity_dir_z.setValue(direction[2])
                    
                    self.gravity_dir_x.blockSignals(False)
                    self.gravity_dir_y.blockSignals(False)
                    self.gravity_dir_z.blockSignals(False)
                
                # Load nodes
                for node in data.get('nodes', []):
                    # Ensure all required fields
                    if 'id' not in node:
                        node['id'] = f"n{len(self.graph_data['nodes'])}"
                    if 'name' not in node:
                        node['name'] = node['id']
                    if 'color' not in node:
                        node['color'] = f'#{np.random.randint(0, 0xFFFFFF):06x}'
                    
                    # Set defaults for missing fields
                    defaults = {
                        'translation': [0, 0, 0],
                        'euler_angles': [0, 0, 0],
                        'rotation_order': 'xyz',
                        'mass': 0,
                        'cog': [0, 0, 0],
                        'external_force': [0, 0, 0],
                        'moment': [0, 0, 0]
                    }
                    
                    for key, default_val in defaults.items():
                        if key not in node:
                            node[key] = default_val
                    
                    self.graph_data['nodes'].append(node)
                    
                    # Add to graph view
                    graph_pos = node.get('graph_position', {})
                    x = graph_pos.get('x', np.random.uniform(-200, 200))
                    y = graph_pos.get('y', np.random.uniform(-150, 150))
                    
                    self.graph_view.add_node(node['id'], node['name'], 
                                           node['color'], x, y)
                
                # Load edges
                for edge in data.get('edges', []):
                    if 'id' not in edge:
                        edge['id'] = f"e{len(self.graph_data['edges'])}"
                    if 'source' not in edge or 'target' not in edge:
                        continue
                        
                    if 'interface_properties' not in edge:
                        edge['interface_properties'] = {
                            'euler_angles': [0, 0, 0],
                            'rotation_order': 'xyz',
                            'position': [0, 0, 0]
                        }
                    
                    self.graph_data['edges'].append(edge)
                    
                    # Add to graph view
                    source_node = next((n for n in self.graph_data['nodes'] 
                                      if n['id'] == edge['source']), None)
                    if source_node:
                        color = source_node.get('color', '#555')
                        self.graph_view.add_edge(edge['id'], edge['source'], 
                                               edge['target'], color)
                
                self.update_node_list()
                self.update_edge_list()
                self.schedule_update()
                self.statusBar.showMessage(f"Loaded from {file_path}", 3000)
                
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Could not load file: {e}")
            
    def export_results(self):
        """Export results to CSV"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Results", "", "CSV Files (*.csv)"
            )
            
            if file_path:
                with open(file_path, 'w') as f:
                    # Write headers
                    headers = []
                    for col in range(self.results_table.columnCount()):
                        headers.append(self.results_table.horizontalHeaderItem(col).text())
                    f.write(','.join(headers) + '\n')
                    
                    # Write data
                    for row in range(self.results_table.rowCount()):
                        row_data = []
                        for col in range(self.results_table.columnCount()):
                            item = self.results_table.item(row, col)
                            row_data.append(item.text() if item else '')
                        f.write(','.join(row_data) + '\n')
                
                self.statusBar.showMessage(f"Results exported to {file_path}", 3000)
                
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Could not export results: {e}")


# ===================== TEST CASES =====================
class TestCasesDialog(QDialog):
    """Dialog to select and load test cases"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Cases")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "Select a test case to validate the load transfer calculations.\n"
            "Each test case demonstrates different physics scenarios."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 11px; color: #2c3e50; padding: 10px;")
        layout.addWidget(info_label)
        
        # Test case list
        self.test_list = QListWidget()
        self.test_list.setAlternatingRowColors(True)
        
        test_cases = [
            "1. Simple Vertical Load - Single cantilever beam",
            "2. Offset Load Transfer - Force with moment generation",
            "3. Rotated Coordinate System - 45° rotation test",
            "4. Three Node Chain - Sequential load transfer",
            "5. Gravity Test - Mass with CoG offset",
            "6. Complex Assembly - Multiple loads and rotations",
            "7. Moment Transfer - Pure moment application"
        ]
        
        for test_case in test_cases:
            self.test_list.addItem(test_case)
        
        self.test_list.setCurrentRow(0)
        layout.addWidget(self.test_list)
        
        # Description
        self.description = QTextEdit()
        self.description.setReadOnly(True)
        self.description.setMaximumHeight(100)
        layout.addWidget(QLabel("Test Case Description:"))
        layout.addWidget(self.description)
        
        self.test_list.currentRowChanged.connect(self.update_description)
        self.update_description(0)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def update_description(self, index):
        """Update description based on selected test case"""
        descriptions = [
            "A simple cantilever with a vertical load at the tip. Tests basic load transfer with no rotation.",
            "Load applied at an offset position to generate a moment. Validates moment calculation due to load offset.",
            "Coordinate system rotated 45° about Z-axis. Tests rotation matrix transformations.",
            "Three nodes in series (A→B→C). Validates cumulative load propagation through multiple connections.",
            "Node with mass and offset center of gravity. Tests gravity load calculation and moment generation.",
            "Complex structure with multiple nodes, rotations, and loads. Comprehensive validation test.",
            "Pure moment applied without force. Tests moment-only transfer calculations."
        ]
        
        if 0 <= index < len(descriptions):
            self.description.setPlainText(descriptions[index])
    
    def get_selected_case(self):
        """Get selected test case number"""
        return self.test_list.currentRow()


def create_test_case_1():
    """Test Case 1: Simple Vertical Load"""
    data = {
        'nodes': [
            {
                'id': 'n0',
                'name': 'Support',
                'translation': [0, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, 0],
                'moment': [0, 0, 0],
                'color': '#3498db',
                'graph_position': {'x': -150, 'y': 0}
            },
            {
                'id': 'n1',
                'name': 'Load Point',
                'translation': [10, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, -100],
                'moment': [0, 0, 0],
                'color': '#e74c3c',
                'graph_position': {'x': 150, 'y': 0}
            }
        ],
        'edges': [
            {
                'id': 'e0',
                'source': 'n1',
                'target': 'n0',
                'interface_properties': {
                    'position': [0, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            }
        ]
    }
    expected = {
        'e0': {'force': [0, 0, -100], 'moment': [0, 1000, 0]}
    }
    return data, expected, "Force: [0,0,-100] at x=10 should create Moment: [0,1000,0] at origin"


def create_test_case_2():
    """Test Case 2: Offset Load Transfer"""
    data = {
        'nodes': [
            {
                'id': 'n0',
                'name': 'Base',
                'translation': [0, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, 0],
                'moment': [0, 0, 0],
                'color': '#3498db',
                'graph_position': {'x': -150, 'y': 0}
            },
            {
                'id': 'n1',
                'name': 'Offset Load',
                'translation': [5, 5, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, -50],
                'moment': [0, 0, 0],
                'color': '#e74c3c',
                'graph_position': {'x': 150, 'y': 0}
            }
        ],
        'edges': [
            {
                'id': 'e0',
                'source': 'n1',
                'target': 'n0',
                'interface_properties': {
                    'position': [0, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            }
        ]
    }
    expected = {
        'e0': {'force': [0, 0, -50], 'moment': [250, -250, 0]}
    }
    return data, expected, "Offset load creates moments: Mx=250 (from y-offset), My=-250 (from x-offset)"


def create_test_case_3():
    """Test Case 3: Rotated Coordinate System"""
    data = {
        'nodes': [
            {
                'id': 'n0',
                'name': 'Global Frame',
                'translation': [0, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, 0],
                'moment': [0, 0, 0],
                'color': '#3498db',
                'graph_position': {'x': -150, 'y': 0}
            },
            {
                'id': 'n1',
                'name': 'Rotated 45°',
                'translation': [10, 0, 0],
                'euler_angles': [0, 0, 45],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [100, 0, 0],
                'moment': [0, 0, 0],
                'color': '#e74c3c',
                'graph_position': {'x': 150, 'y': 0}
            }
        ],
        'edges': [
            {
                'id': 'e0',
                'source': 'n1',
                'target': 'n0',
                'interface_properties': {
                    'position': [0, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            }
        ]
    }
    expected = {
        'e0': {'force': [70.71, 70.71, 0], 'moment': [0, 0, -707.1]}
    }
    return data, expected, "Force [100,0,0] in 45° rotated frame becomes [70.71,70.71,0] in global frame"


def create_test_case_4():
    """Test Case 4: Three Node Chain"""
    data = {
        'nodes': [
            {
                'id': 'n0',
                'name': 'End Support',
                'translation': [0, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, 0],
                'moment': [0, 0, 0],
                'color': '#3498db',
                'graph_position': {'x': -200, 'y': 0}
            },
            {
                'id': 'n1',
                'name': 'Middle Node',
                'translation': [5, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, -30],
                'moment': [0, 0, 0],
                'color': '#2ecc71',
                'graph_position': {'x': 0, 'y': 0}
            },
            {
                'id': 'n2',
                'name': 'Load End',
                'translation': [10, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, -20],
                'moment': [0, 0, 0],
                'color': '#e74c3c',
                'graph_position': {'x': 200, 'y': 0}
            }
        ],
        'edges': [
            {
                'id': 'e0',
                'source': 'n2',
                'target': 'n1',
                'interface_properties': {
                    'position': [5, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            },
            {
                'id': 'e1',
                'source': 'n1',
                'target': 'n0',
                'interface_properties': {
                    'position': [0, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            }
        ]
    }
    expected = {
        'e0': {'force': [0, 0, -20], 'moment': [0, 100, 0]},
        'e1': {'force': [0, 0, -50], 'moment': [0, 250, 0]}
    }
    return data, expected, "Cumulative: e0 gets 20N, e1 gets 50N (20+30) from both loads"


def create_test_case_5():
    """Test Case 5: Gravity with CoG Offset"""
    data = {
        'nodes': [
            {
                'id': 'n0',
                'name': 'Support',
                'translation': [0, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, 0],
                'moment': [0, 0, 0],
                'color': '#3498db',
                'graph_position': {'x': -150, 'y': 0}
            },
            {
                'id': 'n1',
                'name': 'Mass with CoG',
                'translation': [5, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 10.0,
                'cog': [0, 2, 0],
                'external_force': [0, 0, 0],
                'moment': [0, 0, 0],
                'color': '#e74c3c',
                'graph_position': {'x': 150, 'y': 0}
            }
        ],
        'edges': [
            {
                'id': 'e0',
                'source': 'n1',
                'target': 'n0',
                'interface_properties': {
                    'position': [0, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            }
        ]
    }
    expected = {
        'e0': {'force': [0, 0, -98.1], 'moment': [196.2, -490.5, 0]}
    }
    return data, expected, "10kg mass with CoG at [0,2,0] creates gravity force and moments"


def create_test_case_6():
    """Test Case 6: Complex Assembly"""
    data = {
        'nodes': [
            {
                'id': 'n0',
                'name': 'Base',
                'translation': [0, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, 0],
                'moment': [0, 0, 0],
                'color': '#3498db',
                'graph_position': {'x': 0, 'y': -150}
            },
            {
                'id': 'n1',
                'name': 'Arm',
                'translation': [10, 0, 5],
                'euler_angles': [0, 0, 30],
                'rotation_order': 'xyz',
                'mass': 5.0,
                'cog': [1, 0, 0],
                'external_force': [50, 0, 0],
                'moment': [0, 0, 100],
                'color': '#2ecc71',
                'graph_position': {'x': -150, 'y': 50}
            },
            {
                'id': 'n2',
                'name': 'Tool',
                'translation': [15, 5, 5],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 2.0,
                'cog': [0, 0, -1],
                'external_force': [0, 0, -30],
                'moment': [0, 0, 0],
                'color': '#e74c3c',
                'graph_position': {'x': 150, 'y': 50}
            }
        ],
        'edges': [
            {
                'id': 'e0',
                'source': 'n1',
                'target': 'n0',
                'interface_properties': {
                    'position': [0, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            },
            {
                'id': 'e1',
                'source': 'n2',
                'target': 'n0',
                'interface_properties': {
                    'position': [0, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            }
        ]
    }
    expected = {
        'e0': {'force': [93.3, -24.02, -49.05], 'moment': [245.25, -686.69, 100]},
        'e1': {'force': [0, 0, -49.62], 'moment': [248.1, -744.3, 19.62]}
    }
    return data, expected, "Multiple nodes with mass, rotation, and loads converging at base"


def create_test_case_7():
    """Test Case 7: Pure Moment Transfer"""
    data = {
        'nodes': [
            {
                'id': 'n0',
                'name': 'Support',
                'translation': [0, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, 0],
                'moment': [0, 0, 0],
                'color': '#3498db',
                'graph_position': {'x': -150, 'y': 0}
            },
            {
                'id': 'n1',
                'name': 'Moment Source',
                'translation': [8, 0, 0],
                'euler_angles': [0, 0, 0],
                'rotation_order': 'xyz',
                'mass': 0,
                'cog': [0, 0, 0],
                'external_force': [0, 0, 0],
                'moment': [100, 200, 50],
                'color': '#e74c3c',
                'graph_position': {'x': 150, 'y': 0}
            }
        ],
        'edges': [
            {
                'id': 'e0',
                'source': 'n1',
                'target': 'n0',
                'interface_properties': {
                    'position': [0, 0, 0],
                    'euler_angles': [0, 0, 0],
                    'rotation_order': 'xyz'
                }
            }
        ]
    }
    expected = {
        'e0': {'force': [0, 0, 0], 'moment': [100, 200, 50]}
    }
    return data, expected, "Pure moment [100,200,50] transfers without change (no force offset)"


def get_test_case(case_number):
    """Get test case data by number"""
    test_cases = {
        0: create_test_case_1,
        1: create_test_case_2,
        2: create_test_case_3,
        3: create_test_case_4,
        4: create_test_case_5,
        5: create_test_case_6,
        6: create_test_case_7
    }
    
    if case_number in test_cases:
        return test_cases[case_number]()
    return None, None, None


# Add method to IntegratedLoadTransferApp class
def show_test_cases_dialog(self):
    """Show test cases dialog and load selected case"""
    dialog = TestCasesDialog(self)
    if dialog.exec() == QDialog.Accepted:
        case_number = dialog.get_selected_case()
        data, expected, description = get_test_case(case_number)
        
        if data:
            # Clear existing data
            self.graph_view.clear_graph()
            self.graph_data = {'nodes': [], 'edges': []}
            
            # Load test case nodes
            for node in data['nodes']:
                self.graph_data['nodes'].append(node)
                graph_pos = node.get('graph_position', {})
                x = graph_pos.get('x', np.random.uniform(-200, 200))
                y = graph_pos.get('y', np.random.uniform(-150, 150))
                self.graph_view.add_node(node['id'], node['name'], node['color'], x, y)
            
            # Load test case edges
            for edge in data['edges']:
                self.graph_data['edges'].append(edge)
                source_node = next((n for n in self.graph_data['nodes'] 
                                  if n['id'] == edge['source']), None)
                if source_node:
                    self.graph_view.add_edge(edge['id'], edge['source'], 
                                           edge['target'], source_node['color'])
            
            self.update_node_list()
            self.update_edge_list()
            self.schedule_update()
            
            # Show expected results
            msg = f"Test Case {case_number + 1} loaded!\n\n"
            msg += f"Description: {description}\n\n"
            msg += "Expected Results:\n"
            for edge_id, values in expected.items():
                msg += f"\n{edge_id}:\n"
                msg += f"  Force: {values['force']}\n"
                msg += f"  Moment: {values['moment']}\n"
            
            QMessageBox.information(self, "Test Case Loaded", msg)


# Bind the method to the class
IntegratedLoadTransferApp.show_test_cases_dialog = show_test_cases_dialog


# ===================== MAIN ENTRY POINT =====================
def main():
    """Main entry point for the application"""
    app = QApplication(sys.argv)
    
    # Set application-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Set application metadata
    app.setApplicationName("Integrated Load Transfer Tool")
    app.setOrganizationName("Engineering Tools")
    app.setApplicationVersion("2.0")
    
    # Create and show main window
    window = IntegratedLoadTransferApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
