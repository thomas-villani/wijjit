"""Data Entry Demo - Business Form with Multiple Input Types.

This example demonstrates a comprehensive business data entry form:
- Multiple input types (text, select, radio, checkbox, textarea)
- Multi-section form layout
- Field validation and error display
- Data persistence and submission
- Form state management

Run with: python examples/advanced/data_entry_demo.py

Controls:
- Tab/Shift+Tab: Navigate between fields
- q: Quit
"""

from datetime import datetime

from wijjit import Wijjit

# Create app with form state
app = Wijjit(
    initial_state={
        # Customer Information
        "customer_name": "",
        "company_name": "",
        "email": "",
        "phone": "",
        "customer_type": "business",
        # Address
        "street_address": "",
        "city": "",
        "state_province": "",
        "postal_code": "",
        "country": "United States",
        # Order Details
        "product": "",
        "quantity": "1",
        "priority": "normal",
        "delivery_method": "standard",
        # Additional Options
        "gift_wrap": False,
        "insurance": False,
        "signature_required": False,
        # Special Instructions
        "special_instructions": "",
        # Form State
        "validation_errors": [],
        "submitted": False,
        "submission_time": "",
        "order_number": "",
    }
)


def validate_form():
    """Validate all form fields.

    Returns
    -------
    list
        List of validation error messages
    """
    errors = []

    # Validate customer info
    if not app.state.get("customer_name", "").strip():
        errors.append("Customer name is required")

    email = app.state.get("email", "").strip()
    if not email:
        errors.append("Email is required")
    elif "@" not in email:
        errors.append("Email must be valid")

    if not app.state.get("phone", "").strip():
        errors.append("Phone number is required")

    # Validate address
    if not app.state.get("street_address", "").strip():
        errors.append("Street address is required")

    if not app.state.get("city", "").strip():
        errors.append("City is required")

    if not app.state.get("postal_code", "").strip():
        errors.append("Postal code is required")

    # Validate order details
    if not app.state.get("product", "").strip():
        errors.append("Product selection is required")

    try:
        qty = int(app.state.get("quantity", "0"))
        if qty < 1:
            errors.append("Quantity must be at least 1")
        if qty > 1000:
            errors.append("Quantity cannot exceed 1000")
    except ValueError:
        errors.append("Quantity must be a number")

    return errors


@app.view("main", default=True)
def main_view():
    """Main data entry form view.

    Returns
    -------
    dict
        View configuration with template and data
    """
    errors_text = "\n".join(app.state.get("validation_errors", []))
    if not errors_text:
        errors_text = "No errors"

    return {
        "template": """
{% frame title="Business Order Entry Form" border="double" width=110 height=45 %}
  {% vstack spacing=1 padding=1 %}
    {% if not state.submitted %}
      {% vstack spacing=0 %}
        Form Status: {{ "Complete" if state.validation_errors|length == 0 and state.customer_name else "Incomplete" }}
      {% endvstack %}

      {% hstack spacing=2 align_v="top" %}
        {% vstack spacing=1 width=52 %}
          {% frame title="Customer Information" border="single" width="fill" %}
            {% vstack spacing=1 padding=1 %}
              {% vstack spacing=0 %}
                Customer Name: *
              {% endvstack %}
              {% textinput id="customer_name" width=45 placeholder="John Doe" %}{% endtextinput %}

              {% vstack spacing=0 %}
                Company Name:
              {% endvstack %}
              {% textinput id="company_name" width=45 placeholder="Acme Corp" %}{% endtextinput %}

              {% vstack spacing=0 %}
                Email: *
              {% endvstack %}
              {% textinput id="email" width=45 placeholder="john@example.com" %}{% endtextinput %}

              {% vstack spacing=0 %}
                Phone: *
              {% endvstack %}
              {% textinput id="phone" width=45 placeholder="555-1234" %}{% endtextinput %}

              {% radiogroup id="customer_type" name="customer_type" orientation="horizontal" %}
                {% radio value="individual" name="customer_type" %}Individual{% endradio %}
                {% radio value="business" name="customer_type" %}Business{% endradio %}
                {% radio value="government" name="customer_type" %}Government{% endradio %}
              {% endradiogroup %}
            {% endvstack %}
          {% endframe %}

          {% frame title="Shipping Address" border="single" width="fill" %}
            {% vstack spacing=1 padding=1 %}
              {% vstack spacing=0 %}
                Street Address: *
              {% endvstack %}
              {% textinput id="street_address" width=45 placeholder="123 Main St" %}{% endtextinput %}

              {% hstack spacing=2 %}
                {% vstack spacing=0 width=22 %}
                  City: *
                  {% textinput id="city" width=20 placeholder="New York" %}{% endtextinput %}
                {% endvstack %}

                {% vstack spacing=0 width=20 %}
                  State/Province:
                  {% textinput id="state_province" width=18 placeholder="NY" %}{% endtextinput %}
                {% endvstack %}
              {% endhstack %}

              {% hstack spacing=2 %}
                {% vstack spacing=0 width=22 %}
                  Postal Code: *
                  {% textinput id="postal_code" width=20 placeholder="10001" %}{% endtextinput %}
                {% endvstack %}

                {% vstack spacing=0 width=20 %}
                  Country:
                  {% select id="country" width=18 border_style="single" title="" %}
                    United States
                    Canada
                    United Kingdom
                    Germany
                    France
                  {% endselect %}
                {% endvstack %}
              {% endhstack %}
            {% endvstack %}
          {% endframe %}
        {% endvstack %}

        {% vstack spacing=1 width=52 %}
          {% frame title="Order Details" border="single" width="fill" %}
            {% vstack spacing=1 padding=1 %}
              {% vstack spacing=0 %}
                Product: *
              {% endvstack %}
              {% select id="product" width=45 border_style="single" title="" %}
                {\"value\": \"\", \"label\": \"Select a product\"}
                Widget Pro (Model A)
                Widget Deluxe (Model B)
                Widget Premium (Model C)
                Service Package
                Consulting Hours
              {% endselect %}

              {% vstack spacing=0 %}
                Quantity: *
              {% endvstack %}
              {% textinput id="quantity" width=15 placeholder="1" %}{% endtextinput %}

              {% radiogroup id="priority" name="Priority" orientation="horizontal" %}
                {% radio value="low" name="Priority" %}Low{% endradio %}
                {% radio value="normal" name="Priority" %}Normal{% endradio %}
                {% radio value="high" name="Priority" %}High{% endradio %}
                {% radio value="urgent" name="Priority" %}Urgent{% endradio %}
              {% endradiogroup %}

              {% radiogroup id="delivery_method" name="delivery-method" orientation="vertical" %}
                {% radio value="standard" name="delivery-method" %}Standard (5-7 days){% endradio %}
                {% radio value="express" name="delivery-method" %}Express (2-3 days){% endradio %}
                {% radio value="overnight" name="delivery-method" %}Overnight{% endradio %}
              {% endradiogroup %}
            {% endvstack %}
          {% endframe %}

          {% frame title="Additional Options" border="single" width="fill" %}
              {% checkbox id="gift_wrap" label="Gift wrap (+$5)" %}{% endcheckbox %}
              {% checkbox id="insurance" label="Shipping insurance (+$10)" %}{% endcheckbox %}
              {% checkbox id="signature_required" label="Signature required" %}{% endcheckbox %}
          {% endframe %}

          {% frame title="Special Instructions" border="single" width="fill" %}
            {% vstack spacing=0 padding=1 %}
              {% textinput id="special_instructions" width=45 placeholder="Any special requests..." %}{% endtextinput %}
            {% endvstack %}
          {% endframe %}
        {% endvstack %}
      {% endhstack %}

      {% if state.validation_errors %}
        {% frame border="single" %}
          {% vstack spacing=0 padding=1 %}
            Validation Errors:
{{ errors_text }}
          {% endvstack %}
        {% endframe %}
      {% endif %}

      {% hstack spacing=2 %}
        {% button action="submit" %}Submit Order{% endbutton %}
        {% button action="validate" %}Validate Form{% endbutton %}
        {% button action="reset" %}Reset Form{% endbutton %}
        {% button action="quit" %}Quit{% endbutton %}
      {% endhstack %}

    {% else %}
      {% frame title="Order Submitted Successfully!" border="single" %}
        {% vstack spacing=1 padding=2 %}
          {% vstack spacing=0 %}
            Order Number: {{ state.order_number }}
            Submission Time: {{ state.submission_time }}
          {% endvstack %}

          {% vstack spacing=0 %}
            Customer: {{ state.customer_name }}
            {% if state.company_name %}Company: {{ state.company_name }}{% endif %}
            Email: {{ state.email }}
            Phone: {{ state.phone }}
          {% endvstack %}

          {% vstack spacing=0 %}
            Shipping To:
            {{ state.street_address }}
            {{ state.city }}, {{ state.state_province }} {{ state.postal_code }}
            {{ state.country }}
          {% endvstack %}

          {% vstack spacing=0 %}
            Product: {{ state.product }}
            Quantity: {{ state.quantity }}
            Priority: {{ state.priority|capitalize }}
            Delivery: {{ state.delivery_method|capitalize }}
          {% endvstack %}

          {% if state.gift_wrap or state.insurance or state.signature_required %}
            {% vstack spacing=0 %}
              Options: {{ 'Gift Wrap, ' if state.gift_wrap }}{{ 'Insurance, ' if state.insurance }}{{ 'Signature Required' if state.signature_required }}
            {% endvstack %}
          {% endif %}

          {% button action="new_order" %}New Order{% endbutton %}
        {% endvstack %}
      {% endframe %}
    {% endif %}

    {% vstack spacing=0 %}
      * = Required field | [Tab/Shift+Tab] Navigate | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "errors_text": errors_text,
        },
    }


@app.on_action("validate")
def handle_validate(event):
    """Validate form without submitting.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    errors = validate_form()
    app.state["validation_errors"] = errors


@app.on_action("submit")
def handle_submit(event):
    """Submit the order form.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    errors = validate_form()

    if errors:
        app.state["validation_errors"] = errors
        return

    # Generate order number
    order_num = f"ORD-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    app.state["order_number"] = order_num
    app.state["submission_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app.state["submitted"] = True
    app.state["validation_errors"] = []


@app.on_action("reset")
def handle_reset(event):
    """Reset form to defaults.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    # Reset all fields
    app.state["customer_name"] = ""
    app.state["company_name"] = ""
    app.state["email"] = ""
    app.state["phone"] = ""
    app.state["customer_type"] = "business"

    app.state["street_address"] = ""
    app.state["city"] = ""
    app.state["state_province"] = ""
    app.state["postal_code"] = ""
    app.state["country"] = "United States"

    app.state["product"] = ""
    app.state["quantity"] = "1"
    app.state["priority"] = "normal"
    app.state["delivery_method"] = "standard"

    app.state["gift_wrap"] = False
    app.state["insurance"] = False
    app.state["signature_required"] = False

    app.state["special_instructions"] = ""

    app.state["validation_errors"] = []
    app.state["submitted"] = False


@app.on_action("new_order")
def handle_new_order(event):
    """Start a new order.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    handle_reset(event)


@app.on_action("quit")
def handle_quit(event):
    """Quit the application.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.quit()


@app.on_key("q")
def on_quit(event):
    """Handle 'q' key to quit.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.quit()


if __name__ == "__main__":
    import random

    print("Business Data Entry Demo")
    print("=" * 50)
    print()
    print("A comprehensive business order entry form demonstrating:")
    print()
    print("Form Sections:")
    print("  • Customer Information (name, email, phone, type)")
    print("  • Shipping Address (street, city, state, postal, country)")
    print("  • Order Details (product, quantity, priority, delivery)")
    print("  • Additional Options (gift wrap, insurance, signature)")
    print("  • Special Instructions")
    print()
    print("Input Types:")
    print("  • Text inputs (single-line)")
    print("  • Select dropdowns (country, product)")
    print("  • Radio groups (customer type, priority, delivery)")
    print("  • Checkboxes (additional options)")
    print()
    print("Features:")
    print("  • Comprehensive validation")
    print("  • Error display")
    print("  • Multi-section layout")
    print("  • Order confirmation")
    print("  • Reset functionality")
    print()
    print("Starting app...")
    print()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
