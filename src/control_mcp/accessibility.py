"""macOS Accessibility API integration for UI element interaction.

Uses atomacos library which wraps the native macOS Accessibility API.
"""

import time
from typing import Optional, List, Dict, Any, Tuple

# Try to import atomacos for macOS accessibility
try:
    import atomacos
    from atomacos.AXClasses import NativeUIElement
    ACCESSIBILITY_AVAILABLE = True
except ImportError:
    ACCESSIBILITY_AVAILABLE = False
    atomacos = None
    NativeUIElement = None


# Common UI element roles
ROLE_BUTTON = "AXButton"
ROLE_CHECKBOX = "AXCheckBox"
ROLE_RADIO_BUTTON = "AXRadioButton"
ROLE_TEXT_FIELD = "AXTextField"
ROLE_STATIC_TEXT = "AXStaticText"
ROLE_LINK = "AXLink"
ROLE_MENU_ITEM = "AXMenuItem"
ROLE_MENU = "AXMenu"
ROLE_MENU_BAR = "AXMenuBar"
ROLE_MENU_BAR_ITEM = "AXMenuBarItem"
ROLE_WINDOW = "AXWindow"
ROLE_APPLICATION = "AXApplication"
ROLE_GROUP = "AXGroup"
ROLE_TOOLBAR = "AXToolbar"
ROLE_TAB_GROUP = "AXTabGroup"
ROLE_TAB = "AXTab"
ROLE_SCROLL_AREA = "AXScrollArea"
ROLE_LIST = "AXList"
ROLE_TABLE = "AXTable"
ROLE_IMAGE = "AXImage"
ROLE_POP_UP_BUTTON = "AXPopUpButton"


def check_accessibility_permissions() -> bool:
    """
    Check if the application has accessibility permissions.

    Returns:
        True if accessibility is available and permissions are granted
    """
    if not ACCESSIBILITY_AVAILABLE:
        return False

    try:
        # Try to get the frontmost application - this will fail without permissions
        app = atomacos.getAppRefByLocalizedName("Finder")
        return app is not None
    except Exception:
        # Try alternative method
        try:
            apps = atomacos.NativeUIElement.getRunningApps()
            return True
        except Exception:
            return False


def _get_element_info(element) -> Dict[str, Any]:
    """
    Get detailed information about an accessibility element.

    Args:
        element: NativeUIElement to query

    Returns:
        Dictionary with element properties
    """
    info = {}

    try:
        # Get role
        try:
            info["role"] = element.AXRole
        except Exception:
            info["role"] = None

        # Get title
        try:
            info["title"] = element.AXTitle
        except Exception:
            info["title"] = None

        # Get description
        try:
            info["description"] = element.AXDescription
        except Exception:
            info["description"] = None

        # Get value
        try:
            value = element.AXValue
            if value is not None:
                info["value"] = str(value) if not isinstance(value, (int, float, bool)) else value
        except Exception:
            pass

        # Get enabled state
        try:
            info["enabled"] = element.AXEnabled
        except Exception:
            info["enabled"] = None

        # Get identifier
        try:
            info["identifier"] = element.AXIdentifier
        except Exception:
            pass

        # Get position
        try:
            pos = element.AXPosition
            if pos:
                info["position"] = {"x": int(pos.x), "y": int(pos.y)}
        except Exception:
            pass

        # Get size
        try:
            size = element.AXSize
            if size:
                info["size"] = {"width": int(size.width), "height": int(size.height)}
        except Exception:
            pass

        # Calculate center point if we have position and size
        if "position" in info and "size" in info:
            info["center"] = {
                "x": info["position"]["x"] + info["size"]["width"] // 2,
                "y": info["position"]["y"] + info["size"]["height"] // 2,
            }

    except Exception:
        pass

    return info


def _find_elements_recursive(
    element,
    role: Optional[str] = None,
    title: Optional[str] = None,
    title_contains: Optional[str] = None,
    max_depth: int = 10,
    current_depth: int = 0,
    results: Optional[List] = None,
) -> List[Tuple[Any, Dict[str, Any]]]:
    """
    Recursively search for UI elements matching criteria.

    Args:
        element: Starting element
        role: Filter by role (e.g., "AXButton")
        title: Filter by exact title match
        title_contains: Filter by title substring
        max_depth: Maximum recursion depth
        current_depth: Current depth (internal)
        results: Results list (internal)

    Returns:
        List of (element, info) tuples for matching elements
    """
    if results is None:
        results = []

    if current_depth > max_depth:
        return results

    # Get info about current element
    info = _get_element_info(element)

    # Check if this element matches
    matches = True

    if role and info.get("role") != role:
        matches = False

    if title and info.get("title") != title:
        matches = False

    if title_contains:
        elem_title = info.get("title") or ""
        if title_contains.lower() not in str(elem_title).lower():
            matches = False

    if matches and (role or title or title_contains):
        results.append((element, info))

    # Recurse into children
    try:
        children = element.AXChildren
        if children:
            for child in children:
                _find_elements_recursive(
                    child, role, title, title_contains,
                    max_depth, current_depth + 1, results
                )
    except Exception:
        pass

    return results


class AccessibilityController:
    """Controller for macOS Accessibility API interactions."""

    def __init__(self):
        """Initialize the accessibility controller."""
        if not ACCESSIBILITY_AVAILABLE:
            raise RuntimeError(
                "Accessibility API not available. "
                "Install atomacos: pip install atomacos"
            )

    def has_permissions(self) -> bool:
        """Check if accessibility permissions are granted."""
        return check_accessibility_permissions()

    def _get_frontmost_app(self):
        """Get the frontmost application element."""
        try:
            # Get list of running apps and find frontmost
            apps = atomacos.NativeUIElement.getRunningApps()
            for app in apps:
                if app.isActive():
                    # Create app reference by bundle identifier or PID
                    return atomacos.getAppRefByPid(app.processIdentifier())
            return None
        except Exception:
            return None

    def get_focused_application(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently focused application.

        Returns:
            Dictionary with app info, or None if not available
        """
        try:
            app = self._get_frontmost_app()
            if app:
                return _get_element_info(app)
            return None
        except Exception:
            return None

    def get_focused_window(self) -> Optional[Tuple[Any, Dict[str, Any]]]:
        """
        Get the focused window of the focused application.

        Returns:
            Tuple of (element, info) or None
        """
        try:
            app = self._get_frontmost_app()
            if not app:
                return None

            # Try to get focused window
            try:
                window = app.AXFocusedWindow
                if window:
                    return (window, _get_element_info(window))
            except Exception:
                pass

            # Fall back to main window
            try:
                window = app.AXMainWindow
                if window:
                    return (window, _get_element_info(window))
            except Exception:
                pass

            # Try getting first window from windows list
            try:
                windows = app.AXWindows
                if windows and len(windows) > 0:
                    return (windows[0], _get_element_info(windows[0]))
            except Exception:
                pass

            return None
        except Exception:
            return None

    def get_element_at_position(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """
        Get the UI element at a specific screen position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Dictionary with element info, or None
        """
        try:
            # Get system-wide element and find element at position
            system = atomacos.NativeUIElement.systemWideElement()
            element = system.getElementAtPosition((x, y))
            if element:
                return _get_element_info(element)
            return None
        except Exception:
            return None

    def find_buttons(
        self,
        title: Optional[str] = None,
        title_contains: Optional[str] = None,
        in_focused_window: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Find buttons in the UI.

        Args:
            title: Exact button title to match
            title_contains: Substring to match in button title
            in_focused_window: Search only in focused window (default True)

        Returns:
            List of button info dictionaries
        """
        return self.find_elements(
            role=ROLE_BUTTON,
            title=title,
            title_contains=title_contains,
            in_focused_window=in_focused_window,
        )

    def find_elements(
        self,
        role: Optional[str] = None,
        title: Optional[str] = None,
        title_contains: Optional[str] = None,
        in_focused_window: bool = True,
        max_depth: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Find UI elements matching criteria.

        Args:
            role: Element role to match (e.g., "AXButton", "AXTextField")
            title: Exact title to match
            title_contains: Substring to match in title
            in_focused_window: Search only in focused window
            max_depth: Maximum search depth

        Returns:
            List of element info dictionaries
        """
        try:
            # Determine starting element
            if in_focused_window:
                result = self.get_focused_window()
                if not result:
                    return []
                start_element = result[0]
            else:
                app = self._get_frontmost_app()
                if not app:
                    return []
                start_element = app

            # Find matching elements
            matches = _find_elements_recursive(
                start_element,
                role=role,
                title=title,
                title_contains=title_contains,
                max_depth=max_depth,
            )

            return [info for _, info in matches]
        except Exception:
            return []

    def _find_element_by_criteria(
        self,
        role: Optional[str] = None,
        title: Optional[str] = None,
        title_contains: Optional[str] = None,
        in_focused_window: bool = True,
        max_depth: int = 15,
    ) -> Optional[Any]:
        """
        Find a single UI element matching criteria (returns the element itself).

        Returns:
            The element if found, None otherwise
        """
        try:
            if in_focused_window:
                result = self.get_focused_window()
                if not result:
                    return None
                start_element = result[0]
            else:
                app = self._get_frontmost_app()
                if not app:
                    return None
                start_element = app

            matches = _find_elements_recursive(
                start_element,
                role=role,
                title=title,
                title_contains=title_contains,
                max_depth=max_depth,
            )

            if matches:
                return matches[0][0]  # Return first matching element
            return None
        except Exception:
            return None

    def click_button(
        self,
        title: Optional[str] = None,
        title_contains: Optional[str] = None,
        in_focused_window: bool = True,
    ) -> Dict[str, Any]:
        """
        Click a button by its title.

        Args:
            title: Exact button title
            title_contains: Substring in button title
            in_focused_window: Search only in focused window

        Returns:
            Dictionary with result info including:
                - success: Whether the click was performed
                - button: Info about the clicked button (if found)
                - error: Error message (if failed)
        """
        if not title and not title_contains:
            return {"success": False, "error": "Must specify title or title_contains"}

        element = self._find_element_by_criteria(
            role=ROLE_BUTTON,
            title=title,
            title_contains=title_contains,
            in_focused_window=in_focused_window,
        )

        if not element:
            search_term = title or title_contains
            return {
                "success": False,
                "error": f"Button not found: '{search_term}'",
            }

        # Get button info before clicking
        button_info = _get_element_info(element)

        # Check if enabled
        if button_info.get("enabled") is False:
            return {
                "success": False,
                "error": f"Button '{button_info.get('title')}' is disabled",
                "button": button_info,
            }

        # Perform the press action
        try:
            element.Press()
            return {
                "success": True,
                "button": button_info,
                "action": "pressed",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception pressing button: {str(e)}",
                "button": button_info,
            }

    def click_element(
        self,
        role: str,
        title: Optional[str] = None,
        title_contains: Optional[str] = None,
        in_focused_window: bool = True,
    ) -> Dict[str, Any]:
        """
        Click any UI element by its role and title.

        Args:
            role: Element role (e.g., "AXButton", "AXMenuItem", "AXLink")
            title: Exact title
            title_contains: Substring in title
            in_focused_window: Search only in focused window

        Returns:
            Dictionary with result info
        """
        element = self._find_element_by_criteria(
            role=role,
            title=title,
            title_contains=title_contains,
            in_focused_window=in_focused_window,
        )

        if not element:
            search_term = title or title_contains or "(any)"
            return {
                "success": False,
                "error": f"Element not found: role={role}, title='{search_term}'",
            }

        element_info = _get_element_info(element)

        # Try press action
        try:
            element.Press()
            return {
                "success": True,
                "element": element_info,
                "action": "pressed",
            }
        except Exception as e:
            # Try alternative actions
            try:
                # Some elements respond to AXRaise or clicking
                if hasattr(element, 'AXRaise'):
                    element.AXRaise()
                    return {
                        "success": True,
                        "element": element_info,
                        "action": "raised",
                    }
            except Exception:
                pass

            return {
                "success": False,
                "error": f"Failed to activate element: {str(e)}",
                "element": element_info,
            }

    def click_menu_item(
        self,
        menu_path: List[str],
    ) -> Dict[str, Any]:
        """
        Click a menu item by navigating the menu path.

        Args:
            menu_path: List of menu titles from menu bar to item.
                      Example: ["File", "Save As..."]

        Returns:
            Dictionary with result info
        """
        if not menu_path:
            return {"success": False, "error": "Menu path cannot be empty"}

        try:
            app = self._get_frontmost_app()
            if not app:
                return {"success": False, "error": "No focused application"}

            # Get the menu bar
            try:
                menu_bar = app.AXMenuBar
                if not menu_bar:
                    return {"success": False, "error": "Cannot access menu bar"}
            except Exception as e:
                return {"success": False, "error": f"Cannot access menu bar: {e}"}

            current = menu_bar
            for i, menu_title in enumerate(menu_path):
                # Find the menu/menu item with matching title
                try:
                    children = current.AXChildren
                except Exception:
                    return {
                        "success": False,
                        "error": f"No children at menu level {i}: '{menu_title}'"
                    }

                if not children:
                    return {
                        "success": False,
                        "error": f"No children at menu level {i}: '{menu_title}'"
                    }

                found = None
                for child in children:
                    try:
                        child_title = child.AXTitle
                        if child_title and str(child_title) == menu_title:
                            found = child
                            break
                    except Exception:
                        continue

                if not found:
                    available = []
                    for c in children:
                        try:
                            t = c.AXTitle
                            if t:
                                available.append(str(t))
                        except Exception:
                            pass
                    return {
                        "success": False,
                        "error": f"Menu item '{menu_title}' not found. Available: {available}"
                    }

                # If this is not the last item, we need to activate it to open submenu
                if i < len(menu_path) - 1:
                    # Press to open submenu
                    try:
                        found.Press()
                        time.sleep(0.15)  # Wait for menu to open
                    except Exception:
                        pass

                    # Get the submenu
                    try:
                        # Try to get the menu children
                        submenu_children = found.AXChildren
                        if submenu_children and len(submenu_children) > 0:
                            # The submenu is typically the first child that's a menu
                            for sub in submenu_children:
                                try:
                                    if sub.AXRole == "AXMenu":
                                        current = sub
                                        break
                                except Exception:
                                    pass
                            else:
                                current = found
                        else:
                            current = found
                    except Exception:
                        current = found
                else:
                    # This is the final item - press it
                    found_info = _get_element_info(found)
                    try:
                        found.Press()
                        return {
                            "success": True,
                            "menu_item": found_info,
                            "path": menu_path,
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Failed to click menu item: {str(e)}",
                            "menu_item": found_info,
                        }

            return {"success": False, "error": "Unexpected end of menu navigation"}
        except Exception as e:
            return {"success": False, "error": f"Menu navigation failed: {str(e)}"}

    def get_ui_tree(
        self,
        in_focused_window: bool = True,
        max_depth: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get a tree structure of UI elements.

        Args:
            in_focused_window: Only get elements in focused window
            max_depth: Maximum depth to traverse

        Returns:
            List of UI elements with their hierarchy
        """
        try:
            if in_focused_window:
                result = self.get_focused_window()
                if not result:
                    return []
                start_element = result[0]
            else:
                app = self._get_frontmost_app()
                if not app:
                    return []
                start_element = app

            def build_tree(element, depth: int = 0) -> Dict[str, Any]:
                info = _get_element_info(element)

                if depth < max_depth:
                    try:
                        children = element.AXChildren
                        if children:
                            info["children"] = [
                                build_tree(child, depth + 1)
                                for child in children[:50]  # Limit children per level
                            ]
                            if len(children) > 50:
                                info["children_truncated"] = len(children) - 50
                    except Exception:
                        pass

                return info

            return [build_tree(start_element)]
        except Exception:
            return []


# Convenience function for quick button clicks
def click_button_by_name(
    name: str,
    exact_match: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to quickly click a button by name.

    Args:
        name: Button name (or substring)
        exact_match: If True, match exact title; if False, match substring

    Returns:
        Result dictionary
    """
    try:
        controller = AccessibilityController()
        if not controller.has_permissions():
            return {
                "success": False,
                "error": "Accessibility permissions not granted. Enable in System Preferences > Privacy & Security > Accessibility"
            }

        if exact_match:
            return controller.click_button(title=name)
        else:
            return controller.click_button(title_contains=name)
    except Exception as e:
        return {"success": False, "error": str(e)}
