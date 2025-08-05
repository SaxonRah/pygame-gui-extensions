

![PyGame GUI Extensions](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/pygame_gui_extensions.png "PyGame GUI Extensions")

# PyGame GUI Extensions - [Version 0.1]

Well-built GUI widgets built on top of pygame-ce and pygame-gui for building tools easier with pygame-ce and pygame-gui.

This extension is being built to facilitate [PySpine](https://github.com/SaxonRah/PySpine) and [StoryForge](https://github.com/SaxonRah/StoryForge). 

---
# Completed Version 0.1 Panels
### **Hierarchy Panel**
Tree-view widget for organizing data structures:
- Expandable/collapsible folder and item nodes
- Drag and drop reordering with visual feedback
- Custom icons and theming support
- Mouse and keyboard navigation
- Events for selection, expansion, and context menus
- Perfect for file explorers, scene graphs, or project trees
![Hierarchy Panel](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/HierarchyPanel.png "Hierarchy Panel")

### **Property Inspector Panel**
Comprehensive property editing interface:
- Multiple property types (text, numbers, colors, vectors, dropdowns)
- Collapsible sections with validation
- Live editing with real-time feedback
- Advanced/basic property filtering
- Rich controls including color pickers and sliders
- Essential companion to hierarchy panels for object editing
![Property Panel](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/PropertyPanel.png "Property Panel")

### **Node Editor Panel**
Visual programming interface:
- Draggable nodes with input/output sockets
- Bezier curve connections
- Node libraries and search
- Zoom/pan navigation
- Would pair excellently with the property inspector
![Node Editor Panel](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/NodeEditorPanel.png "Node Editor Panel")

### **Timeline/Animation Panel**
For keyframe animation:
- Scrubbing timeline with frame markers
- Keyframe editing and curves
- Layer management
- Playback controls
- Integration with the hierarchy for animated objects
![Timeline Panel](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/TimelinePanel.png "Timeline Panel")

### **Mini-map/Navigator Panel**
For large content areas:
- Thumbnail view of large canvases
- Viewport indicator and navigation
- Zoom controls
- Works great with node editors or large hierarchies
![Navigator Panel](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/NavigatorPanel.png "Navigator Panel")

### **Asset Browser Panel**
Media asset management:
- Preview thumbnails for images/models
- Metadata display and editing
- Import/export functionality
- Search and tagging
- Drag-and-drop to hierarchy
![Asset Browser Panel](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/AssetBrowserPanel.png "Asset Browser Panel")


### **Console/Terminal Panel**
A powerful console for logging, command execution, and REPL functionality:
- Command history with up/down arrows
- Auto-completion and syntax highlighting
- Scrollable output with filtering
- Command aliases and macros
- Integration with Python `exec()` for live scripting
![Console Panel](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/ConsolePanel.png "Console Panel")

---
# Examples:

### **Skeletal Animation Example**
A basic example showing off integration with Hierarchy, Property, and Timeline panels.
![Skeletal Animation Example](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/Example_SkeletonAnimation.png "Skeletal Animation Example")

---

# Work in Progress:

### 6. **Tool Palette Panel**
Organized tool selection:
- Categorized tool groups
- Search and favorites
- Customizable layouts (grid/list)
- Tool descriptions and shortcuts
![Tool Palette Panel](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/ToolPalettePanel.png "Tool Palette Panel")

### 3. **Docking System**
A framework for dockable panels:
- Drag-and-drop panel arrangement
- Tabbed panel groups
- Splitter controls for resizing
- Save/restore layouts
- Would make the hierarchy + property panels even more useful
![Docking System](https://github.com/SaxonRah/pygame-gui-extensions/blob/main/images/DockingSystem.png "Docking System")

---

## Future Panels
### 2. **Code Editor Panel** 
A syntax-highlighted text editor:
- Line numbers and folding
- Find/replace with regex support
- Bracket matching and indentation guides
- Multiple language support (Python, JSON, etc.)
- Integration with the property inspector for script editing
  
### 4. **File Browser Panel**
Enhanced file system navigation:
- Thumbnail previews for images
- File type filtering and search
- Breadcrumb navigation
- Recent files and bookmarks
- Integration with the hierarchy panel for project files
  
### 5. **Data Grid/Table Panel**
Spreadsheet-like component:
- Sortable columns with custom comparers
- In-cell editing with validation
- Row selection and highlighting
- Export to CSV/JSON
- Perfect complement to the property inspector
  
### 7. **Chart/Graph Panel**
Data visualization component:
- Line charts, bar charts, pie charts
- Real-time data updates
- Interactive legends and tooltips
- Export to image formats
- Great for debugging and analytics

### 8. **Log Viewer Panel**
Advanced logging interface:
- Filtering by level/category
- Search and highlighting
- Timestamped entries
- Export and clearing functions

---
