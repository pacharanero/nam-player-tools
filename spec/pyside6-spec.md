## PySide6 Dialog & Widget Syncing Best Practices

### Lessons Learned from Modal Implementation

- **Always Sync Sliders and Spinboxes Both Ways:**

  - When using a slider and spinbox for the same value, connect their valueChanged signals to each other so that changes in either widget update the other.
  - Example: `slider.valueChanged.connect(lambda v: spinbox.setValue(v / factor))` and `spinbox.valueChanged.connect(lambda v: slider.setValue(int(v * factor)))`.

- **Save the Last User-Set Value:**

  - In the dialog's result method, always read the value from the widget that the user most likely interacted with last (often the slider), or ensure the spinbox is always updated by the slider.
  - This prevents cases where the value is not saved if the user only moves the slider and does not touch the spinbox.

- **Store Key Widgets as Attributes:**

  - If you need to access a widget's value outside the constructor (e.g., in `get_result`), store it as `self.widget_name`.

- **Import All PySide6 Widgets at the Top:**

  - For clarity and maintainability, import all required PySide6 widgets at the top of the file, not inside functions or methods.

- **UI/UX Patterns:**

  - Use a two-column layout for dialogs with many fields to improve readability.
  - For color fields, provide both a hex input and a color picker for flexibility.
  - Use sliders for quick adjustment of numeric values, but always pair with a spinbox for precision.

- **Testing:**
  - After implementing syncing, test that all changes (via slider or spinbox) are reflected in the saved result.
