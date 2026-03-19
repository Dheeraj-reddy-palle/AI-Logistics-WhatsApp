"""
Main Conversation Agent — State-machine driven, fully local, no paid APIs.
Handles all 10 logistics scenarios using rule-based NLP + Redis state management.
"""
import logging
import uuid
from decimal import Decimal

from app.config.settings import settings
from app.ai.state_machine import StateMachine
from app.ai.nlp_engine import parse_message
from app.services.location_resolver import resolve_location
from app.services.pricing_service import PricingService

logger = logging.getLogger(__name__)

state_manager = StateMachine(redis_url=settings.REDIS_URL)


async def handle_incoming_message(phone_number: str, message_text: str, message_id: str) -> dict:
    """
    Entry point for all incoming messages.
    Returns standardized response dict:
    {"reply": "...", "state": "...", "booking_id": optional}
    """
    logger.info(f"🚀 [REQUEST START] phone={phone_number} msg_id={message_id}")
    
    # 1. IDEMPOTENCY CHECK (Correction #1)
    if not await state_manager.check_idempotency(message_id):
        logger.warning(f"Duplicate message_id {message_id} rejected.")
        return {
            "reply": "Message already processed.",
            "state": "duplicate",
            "booking_id": None,
        }

    # 2. CHECK FOR CANCEL/RESET (Correction #2)
    if state_manager.is_cancel_command(message_text):
        await state_manager.clear_state(phone_number)
        logger.info(f"[{phone_number}] State reset by user command.")
        return {
            "reply": "✅ Your session has been reset. Send a new message to start fresh!",
            "state": "idle",
            "booking_id": None,
        }

    try:
        # 3. FETCH USER STATE
        state = await state_manager.get_state(phone_number)
        current_flow = state.get("current_flow", "idle")
        context = state.get("context", {})

        # 4. Parse message
        parsed = parse_message(message_text)
        logger.info(f"[{phone_number}] State={current_flow} | Intent={parsed.intent} | Text={message_text[:50]}")

        # 5. ROUTE BASED ON STATE
        if current_flow == "idle":
            result = await _handle_idle(phone_number, message_text, parsed, context)
        elif current_flow == "collecting_pickup":
            result = await _handle_collecting_pickup(phone_number, message_text, parsed, context)
        elif current_flow == "collecting_drop":
            result = await _handle_collecting_drop(phone_number, message_text, parsed, context)
        elif current_flow == "collecting_weight":
            result = await _handle_collecting_weight(phone_number, message_text, parsed, context)
        elif current_flow == "collecting_passenger":
            result = await _handle_collecting_passenger(phone_number, message_text, parsed, context)
        elif current_flow == "booking_confirmed":
            result = await _handle_booking_confirmed(phone_number, message_text, parsed, context)
        elif current_flow == "tracking":
            result = await _handle_tracking(phone_number, message_text, parsed, context)
        else:
            result = await _handle_idle(phone_number, message_text, parsed, context)
            
        logger.info(f"🏁 [REQUEST END] phone={phone_number} msg_id={message_id} -> state={result.get('state')}")
        return result

    except Exception as e:
        logger.error(f"💥 [ERROR] Processing failed for msg_id {message_id}: {e}", exc_info=True)
        return {
            "reply": "Sorry, I didn’t understand or there was a temporary issue. Please try again or type 'start over'.",
            "state": "error",
            "booking_id": None,
        }


# ─── STATE HANDLERS ──────────────────────────────────────────────────

async def _handle_idle(phone: str, text: str, parsed, context: dict) -> dict:
    """Handle messages when user is in idle state"""
    
    # Check for remote booking
    if parsed.is_remote:
        await state_manager.update_state(phone, "collecting_pickup", {
            "is_remote": True,
            "booked_by": phone,
            "service_type": parsed.service_type,
        })
        svc = "🚕 cab" if parsed.service_type == "cab" else "📦 delivery"
        return {
            "reply": (
                f"Remote {svc} booking detected!\n"
                "I'll help you book for someone else.\n\n"
                "First, please share the **pickup location** 📍\n"
                "Send coordinates (lat,lng) or a Google Maps link for exact location."
            ),
            "state": "collecting_pickup",
            "booking_id": None,
        }
    
    # Check for greeting
    if parsed.intent == "greeting":
        return {
            "reply": (
                "👋 Welcome to Logistics AI!\n"
                "I can help you:\n"
                "🚕 **Book a cab** — say 'book cab from A to B'\n"
                "📦 **Book a delivery** — say 'send 200kg from A to B'\n"
                "📍 **Track** — say 'track'\n\n"
                "Examples:\n"
                "• 'Book cab from RGIA to Gachibowli'\n"
                "• 'Send 200kg from 17.24,78.43 to 17.44,78.35'"
            ),
            "state": "idle",
            "booking_id": None,
        }
    
    # Check for tracking
    if parsed.intent == "tracking":
        return await _handle_tracking(phone, text, parsed, context)
    
    # Check for booking intent with full details
    if parsed.intent == "booking" and parsed.pickup and parsed.drop:
        # User provided both pickup and drop in one message
        # Validate both locations independently (Correction #3)
        pickup_result = resolve_location(parsed.pickup)
        drop_result = resolve_location(parsed.drop)
        
        errors = []
        if pickup_result.precision == "low":
            errors.append(f"📍 Pickup location \"{parsed.pickup}\" is too vague.")
        if drop_result.precision == "low":
            errors.append(f"📍 Drop location \"{parsed.drop}\" is too vague.")
        
        if errors:
            # Save what we have, ask for clarification
            updates = {}
            if pickup_result.precision == "exact":
                updates["pickup"] = pickup_result.display_name
                updates["pickup_lat"] = pickup_result.lat
                updates["pickup_lng"] = pickup_result.lng
            if drop_result.precision == "exact":
                updates["drop"] = drop_result.display_name
                updates["drop_lat"] = drop_result.lat
                updates["drop_lng"] = drop_result.lng
            
            # Determine next state
            if pickup_result.precision == "low" and drop_result.precision == "low":
                next_state = "collecting_pickup"
                updates["pending_drop"] = parsed.drop
            elif pickup_result.precision == "low":
                next_state = "collecting_pickup"
            else:
                next_state = "collecting_drop"
            
            await state_manager.update_state(phone, next_state, updates)
            
            error_msg = "\n".join(errors)
            return {
                "reply": (
                    f"{error_msg}\n\n"
                    "Please share exact location using:\n"
                    "• Coordinates (e.g., 17.2403,78.4294)\n"
                    "• Google Maps link 📍"
                ),
                "state": next_state,
                "booking_id": None,
            }
        
        # Both locations are precise — determine next step based on service type
        is_cab = parsed.service_type == "cab"
        
        updates = {
            "pickup": pickup_result.display_name,
            "pickup_lat": pickup_result.lat,
            "pickup_lng": pickup_result.lng,
            "drop": drop_result.display_name,
            "drop_lat": drop_result.lat,
            "drop_lng": drop_result.lng,
            "service_type": parsed.service_type,
        }
        
        if is_cab:
            # Cab bookings skip weight — go directly to quote
            updates["weight"] = 0
            updates["vehicle_type"] = "car"
            await state_manager.update_state(phone, "booking_confirmed", updates)
            return await _generate_quote_and_confirm(phone)
        
        # Cargo: need weight
        await state_manager.update_state(phone, "collecting_weight", updates)
        
        # If weight was also provided in the same message
        if parsed.weight is not None:
            return await _process_weight(phone, parsed.weight)
        
        return {
            "reply": (
                f"✅ Pickup: {pickup_result.display_name}\n"
                f"✅ Drop: {drop_result.display_name}\n\n"
                "📦 How much does the cargo weigh? (in kg)\n"
                "Example: '200kg' or '150'"
            ),
            "state": "collecting_weight",
            "booking_id": None,
        }
    
    # Booking intent without full details
    if parsed.intent == "booking":
        await state_manager.update_state(phone, "collecting_pickup", {
            "service_type": parsed.service_type,
        })
        svc = "🚕 cab" if parsed.service_type == "cab" else "📦 delivery"
        return {
            "reply": (
                f"Let's set up your {svc}!\n\n"
                "Please share the **pickup location** 📍\n"
                "Send coordinates (lat,lng) or a Google Maps link for exact location."
            ),
            "state": "collecting_pickup",
            "booking_id": None,
        }
        
    # User started by just pasting a location
    if parsed.intent == "location_input":
        location = resolve_location(text)
        if location.precision == "exact":
            await state_manager.update_state(phone, "collecting_drop", {
                "pickup": location.display_name,
                "pickup_lat": location.lat,
                "pickup_lng": location.lng,
                "service_type": parsed.service_type,
            })
            svc = "🚕 cab" if parsed.service_type == "cab" else "📦 delivery"
            return {
                "reply": (
                    f"✅ Pickup set for {svc}: {location.display_name}\n\n"
                    "Now, please share the **drop-off location** 📍\n"
                    "(If you meant to book a cab, just reply 'cab' along with the destination)"
                ),
                "state": "collecting_drop",
                "booking_id": None,
            }
    
    # Unknown / catch-all
    return {
        "reply": (
            "👋 I'm the Logistics AI Assistant!\n"
            "Would you like to:\n"
            "🚕 **Book a cab** — 'book cab from A to B'\n"
            "📦 **Book a delivery** — 'send 200kg from A to B'\n"
            "📍 **Track** — say 'track'\n\n"
            "Examples:\n"
            "• 'Book cab from RGIA to Kondapur'\n"
            "• 'Send 200kg from 17.24,78.43 to 17.44,78.35'"
        ),
        "state": "idle",
        "booking_id": None,
    }


async def _handle_collecting_pickup(phone: str, text: str, parsed, context: dict) -> dict:
    """Handle state: collecting pickup location"""
    
    location = resolve_location(text)
    
    if location.precision == "low":
        return {
            "reply": (
                f"📍 \"{text}\" is not precise enough for pickup.\n\n"
                "Please share exact location using:\n"
                "• Coordinates (e.g., 17.2403,78.4294)\n"
                "• Google Maps link 📍"
            ),
            "state": "collecting_pickup",
            "booking_id": None,
        }
    
    # Update service type if user clarified it
    service_type = parsed.service_type if parsed.service_type == "cab" else context.get("service_type", "cargo")
    
    # Save pickup and move to drop
    updates = {
        "pickup": location.display_name,
        "pickup_lat": location.lat,
        "pickup_lng": location.lng,
        "service_type": service_type,
    }
    
    # Check if we had a pending drop from the initial message
    pending_drop = context.get("pending_drop")
    if pending_drop:
        drop_result = resolve_location(pending_drop)
        if drop_result.precision == "exact":
            updates["drop"] = drop_result.display_name
            updates["drop_lat"] = drop_result.lat
            updates["drop_lng"] = drop_result.lng
            updates["pending_drop"] = None
            await state_manager.update_state(phone, "collecting_weight", updates)
            return {
                "reply": (
                    f"✅ Pickup: {location.display_name}\n"
                    f"✅ Drop: {drop_result.display_name}\n\n"
                    "📦 How much does the cargo weigh? (in kg)"
                ),
                "state": "collecting_weight",
                "booking_id": None,
            }
    
    await state_manager.update_state(phone, "collecting_drop", updates)
    
    return {
        "reply": (
            f"✅ Pickup set: {location.display_name}\n\n"
            "Now, please share the **drop-off location** 📍\n"
            "Send coordinates (lat,lng) or a Google Maps link."
        ),
        "state": "collecting_drop",
        "booking_id": None,
    }


async def _handle_collecting_drop(phone: str, text: str, parsed, context: dict) -> dict:
    """Handle state: collecting drop location"""
    
    location = resolve_location(text)
    
    if location.precision == "low":
        return {
            "reply": (
                f"📍 \"{text}\" is not precise enough for drop-off.\n\n"
                "Please share exact location using:\n"
                "• Coordinates (e.g., 17.4399,78.3489)\n"
                "• Google Maps link 📍"
            ),
            "state": "collecting_drop",
            "booking_id": None,
        }
    
    # Update service type if user clarified it
    service_type = parsed.service_type if parsed.service_type == "cab" else context.get("service_type", "cargo")
    
    updates = {
        "drop": location.display_name,
        "drop_lat": location.lat,
        "drop_lng": location.lng,
        "service_type": service_type,
    }
    
    is_cab = service_type == "cab"
    
    if is_cab:
        updates["weight"] = 0
        updates["vehicle_type"] = "car"
        await state_manager.update_state(phone, "booking_confirmed", updates)
        return await _generate_quote_and_confirm(phone)
    
    await state_manager.update_state(phone, "collecting_weight", updates)
    
    return {
        "reply": (
            f"✅ Drop-off set: {location.display_name}\n\n"
            "📦 How much does the cargo weigh? (in kg)\n"
            "Example: '200kg' or '150'"
        ),
        "state": "collecting_weight",
        "booking_id": None,
    }


async def _handle_collecting_weight(phone: str, text: str, parsed, context: dict) -> dict:
    """Handle state: collecting weight"""
    import re
    
    # Extract weight from text
    weight = parsed.weight
    if weight is None:
        # Try plain number
        match = re.search(r'(-?\d+(?:\.\d+)?)', text)
        if match:
            weight = float(match.group(1))
    
    # Validate weight (Correction #8)
    if weight is None:
        return {
            "reply": (
                "❌ I couldn't understand the weight.\n"
                "Please enter weight in kg (e.g., '200kg' or '150')."
            ),
            "state": "collecting_weight",
            "booking_id": None,
        }
    
    if weight <= 0:
        return {
            "reply": "❌ Weight must be a positive number. Please enter a valid weight in kg.",
            "state": "collecting_weight",
            "booking_id": None,
        }
    
    if weight > 50000:
        return {
            "reply": "❌ Weight exceeds maximum limit (50,000 kg). Please check and re-enter.",
            "state": "collecting_weight",
            "booking_id": None,
        }
    
    return await _process_weight(phone, weight)


async def _process_weight(phone: str, weight: float) -> dict:
    """Process validated weight — move to passenger collection or booking confirmation"""
    
    state = await state_manager.get_state(phone)
    context = state.get("context", {})
    is_remote = context.get("is_remote", False)
    
    await state_manager.update_state(phone, 
        "collecting_passenger" if is_remote else "booking_confirmed",
        {"weight": weight}
    )
    
    if is_remote:
        # Need passenger phone for remote booking (Correction #7)
        return {
            "reply": (
                f"✅ Weight: {weight}kg\n\n"
                "Since this is a booking for someone else, "
                "please provide the **passenger's phone number** 📱"
            ),
            "state": "collecting_passenger",
            "booking_id": None,
        }
    
    # Calculate quote and confirm
    return await _generate_quote_and_confirm(phone)


async def _handle_collecting_passenger(phone: str, text: str, parsed, context: dict) -> dict:
    """Handle state: collecting passenger phone for remote bookings"""
    import re
    
    # Extract phone number (Correction #7)
    phone_match = re.search(r'(\+?\d{10,13})', text.replace(" ", "").replace("-", ""))
    
    if not phone_match:
        return {
            "reply": (
                "❌ Please provide a valid phone number (10+ digits).\n"
                "Example: 9876543210"
            ),
            "state": "collecting_passenger",
            "booking_id": None,
        }
    
    passenger_phone = phone_match.group(1)
    
    await state_manager.update_state(phone, "booking_confirmed", {
        "passenger_phone": passenger_phone,
    })
    
    return await _generate_quote_and_confirm(phone)


async def _generate_quote_and_confirm(phone: str) -> dict:
    """Generate price quote from collected data and present to user"""
    
    state = await state_manager.get_state(phone)
    context = state.get("context", {})
    
    pickup_lat = context.get("pickup_lat")
    pickup_lng = context.get("pickup_lng")
    drop_lat = context.get("drop_lat")
    drop_lng = context.get("drop_lng")
    weight = context.get("weight", 0)
    vehicle_type = context.get("vehicle_type", "truck")
    
    if not all([pickup_lat, pickup_lng, drop_lat, drop_lng]):
        await state_manager.clear_state(phone)
        return {
            "reply": "❌ Missing location data. Please start over.",
            "state": "idle",
            "booking_id": None,
        }
    
    # Generate quote
    quote = PricingService.generate_quote(
        pickup_lat, pickup_lng,
        drop_lat, drop_lng,
        weight, vehicle_type
    )
    
    # Store quote in context
    await state_manager.update_state(phone, "booking_confirmed", {
        "price_quote": float(quote["price"]),
    })
    
    pickup_name = context.get("pickup", "Pickup")
    drop_name = context.get("drop", "Drop")
    is_remote = context.get("is_remote", False)
    passenger_phone = context.get("passenger_phone", "")
    is_cab = context.get("service_type") == "cab"
    
    if is_cab:
        reply_parts = [
            "🚕 **Cab Booking Summary**\n",
            f"📍 Pickup: {pickup_name}",
            f"📍 Drop: {drop_name}",
            f"📏 Distance: {quote['distance_km']}km",
            f"⏱️ ETA: ~{quote.get('duration_min', '?')} min",
            f"💰 **Estimated Fare: ₹{quote['price']}**",
        ]
    else:
        reply_parts = [
            "📋 **Booking Summary**\n",
            f"📍 Pickup: {pickup_name}",
            f"📍 Drop: {drop_name}",
            f"📦 Weight: {weight}kg",
            f"🚛 Vehicle: {vehicle_type.title()}",
            f"📏 Distance: {quote['distance_km']}km",
            f"⏱️ ETA: ~{quote.get('duration_min', '?')} min",
            f"💰 **Estimated Price: ₹{quote['price']}**",
            f"\n{quote['disclaimer']}",
        ]
    
    if is_remote and passenger_phone:
        reply_parts.insert(-1, f"👤 Passenger: {passenger_phone}")
    
    reply_parts.append("\n✅ Reply **'confirm'** to book, or **'cancel'** to start over.")
    
    # Simulate realistic delay before returning quote
        # Check precision
    
    return {
        "reply": "\n".join(reply_parts),
        "state": "booking_confirmed",
        "booking_id": None,
    }


async def _handle_booking_confirmed(phone: str, text: str, parsed, context: dict) -> dict:
    """Handle state: booking confirmed — waiting for user to confirm or cancel"""
    
    if parsed.intent == "confirmation":
        return await _create_booking(phone, context)
    
    # User didn't confirm
    return {
        "reply": "Please reply **'confirm'** to proceed with booking, or **'cancel'** to start over.",
        "state": "booking_confirmed",
        "booking_id": None,
    }


async def _create_booking(phone: str, context: dict) -> dict:
    """Actually create the booking in the database and assign a driver"""
    from app.db.session import AsyncSessionLocal
    from app.services.booking_service import BookingService
    from app.services.driver_service import DriverService
    
    state = await state_manager.get_state(phone)
    ctx = state.get("context", {})
    
    try:
        async with AsyncSessionLocal() as session:
            booking_svc = BookingService(session)
            driver_svc = DriverService(session)
            
            # Create booking
            booking = await booking_svc.create_booking(
                customer_phone=phone,
                pickup_address=ctx.get("pickup", "Unknown"),
                drop_address=ctx.get("drop", "Unknown"),
                pickup_lat=ctx.get("pickup_lat", 0),
                pickup_lng=ctx.get("pickup_lng", 0),
                drop_lat=ctx.get("drop_lat", 0),
                drop_lng=ctx.get("drop_lng", 0),
                declared_weight=ctx.get("weight", 0),
                vehicle_type=ctx.get("vehicle_type", "truck"),
                price_quote=Decimal(str(ctx.get("price_quote", 0))),
                booked_by=ctx.get("booked_by", phone),
                passenger_phone=ctx.get("passenger_phone"),
            )
            
            booking_id = str(booking.id)
            
            # Try to auto-assign nearest driver (Correction #5)
            driver = await driver_svc.find_nearest_available_driver(
                lat=ctx.get("pickup_lat", 0),
                lng=ctx.get("pickup_lng", 0),
                vehicle_type=ctx.get("vehicle_type"),
            )
            
            driver_msg = ""
            if driver:
                await booking_svc.assign_driver(booking.id, driver.id)
                await driver_svc.mark_unavailable(driver.id)
                
                # Simulate driver taking time to look at the app and accept
                # Mock driver acceptance flow
                
                driver_msg = (
                    f"\n\n🚛 Driver assigned: **{driver.name}**\n"
                    f"Waiting for driver to accept...\n"
                    f"Driver will receive booking details shortly."
                )
                
                # Log what would be sent to driver (mock WhatsApp)
                logger.info(
                    f">>> [MOCK WHATSAPP TO DRIVER {driver.phone}]: "
                    f"New booking #{booking_id[:8]}! "
                    f"Pickup: {ctx.get('pickup')} | "
                    f"Drop: {ctx.get('drop')} | "
                    f"Weight: {ctx.get('weight')}kg | "
                    f"Reply ACCEPT to take this job."
                )
            else:
                driver_msg = "\n\n⏳ Looking for available drivers in your area..."
            
            # Update state and auto-reset (Correction #2 — auto-reset after booking)
            await state_manager.update_state(phone, "tracking", {
                "booking_id": booking_id,
            })
            
            return {
                "reply": (
                    f"🎉 **Booking Confirmed!**\n"
                    f"📋 Booking ID: `{booking_id[:8]}`\n"
                    f"💰 Estimated Price: ₹{ctx.get('price_quote', 0)}"
                    f"{driver_msg}"
                ),
                "state": "tracking",
                "booking_id": booking_id,
            }
    
    except Exception as e:
        logger.error(f"Booking creation failed for {phone}: {e}")
        await state_manager.clear_state(phone)
        return {
            "reply": "❌ Sorry, something went wrong creating your booking. Please try again.",
            "state": "idle",
            "booking_id": None,
        }


async def _handle_tracking(phone: str, text: str, parsed, context: dict) -> dict:
    """Handle state: tracking — show driver location"""
    from app.services.tracking_service import TrackingService
    
    booking_id = context.get("booking_id")
    
    if not booking_id:
        await state_manager.clear_state(phone)
        return {
            "reply": "No active booking to track. Would you like to book a delivery?",
            "state": "idle",
            "booking_id": None,
        }
    
    # Simulate network delay retrieving driver tracking
        tracking_link = get_tracking_link(booking_id)
    
    # Check Redis for driver location
    location = await state_manager.get_driver_location(booking_id)
    
    if location:
        # Correction #6: Only show link if location exists
        msg = TrackingService.format_tracking_message(location["lat"], location["lng"])
    else:
        msg = TrackingService.no_location_message()
    
    return {
        "reply": f"📋 Booking: `{booking_id[:8]}`\n{msg}",
        "state": "tracking",
        "booking_id": booking_id,
    }
