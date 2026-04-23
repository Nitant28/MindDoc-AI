"""
accessibility_manager.py
Accessibility: Screen reader, high-contrast mode, keyboard navigation support.
"""

class AccessibilityManager:
    def __init__(self):
        self.screen_reader_enabled = False
        self.high_contrast_mode = False
        self.keyboard_navigation_enabled = True

    def enable_screen_reader(self):
        self.screen_reader_enabled = True

    def enable_high_contrast(self):
        self.high_contrast_mode = True

    def enable_keyboard_navigation(self):
        self.keyboard_navigation_enabled = True

accessibility_manager = AccessibilityManager()

# Example usage:
# accessibility_manager.enable_screen_reader()
# accessibility_manager.enable_high_contrast()
