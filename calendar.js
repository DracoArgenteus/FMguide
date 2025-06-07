// calendar.js

/**
 * Renders the collaborative calendar view into a given container element.
 * @param {HTMLElement} calendarEl - The container element for the calendar grid.
 * @param {Array} allEvents - The complete list of event objects from Firestore.
 * @param {Object} allSignups - The map of signups, e.g., { eventId: { userId: { docId, userEmail } } }.
 * @param {Object} delegationConfig - The configuration object for team members (email, name, color).
 * @param {Object} everyoneColorConfig - The configuration for the "everyone attending" color.
 */
export function renderCalendar(calendarEl, allEvents, allSignups, delegationConfig, everyoneColorConfig) {
    if (!calendarEl) {
        console.error("Calendar container element not provided.");
        return;
    }
    console.log("Rendering calendar with latest event and signup data...");

    const days = ["Onsdag", "Torsdag", "Fredag", "Lørdag"];
    const startHour = 6;
    const endHour = 24; // Renders up to the 21:xx timeslot

    // 1. Build the Calendar Grid Structure (Headers and Timeslots)
    let html = '<div class="time-label"></div>'; // Top-left empty corner
    days.forEach(day => {
        html += `<div class="calendar-header">${day}</div>`;
    });

    for (let hour = startHour; hour < endHour; hour++) {
        html += `<div class="time-label">${String(hour).padStart(2, '0')}:00</div>`;
        days.forEach(day => {
            // Each timeslot cell gets a unique data attribute for easy targeting
            html += `<div class="calendar-timeslot" data-day="${day}" data-hour="${hour}"></div>`;
        });
    }
    calendarEl.innerHTML = html;

    // 2. Group Events by Timeslot for Overlap Calculation
    const eventsToRender = allEvents.filter(e => days.includes(e.Weekday));
    const eventLayout = {}; // Key: "Weekday-Hour", Value: [event, event, ...]

    eventsToRender.forEach(event => {
        if (!event.TimeRange) return;
        const timeMatch = event.TimeRange.match(/^(\d{2}):(\d{2})/);
        if (!timeMatch) return;

        const startHourEvent = parseInt(timeMatch[1], 10);
        const slotKey = `${event.Weekday}-${startHourEvent}`;
        if (!eventLayout[slotKey]) {
            eventLayout[slotKey] = [];
        }
        eventLayout[slotKey].push(event);
    });

    // 3. Render each event onto the grid
    for (const slotKey in eventLayout) {
        const eventsInSlot = eventLayout[slotKey];
        const [day, hour] = slotKey.split('-');
        const slotEl = calendarEl.querySelector(`[data-day="${day}"][data-hour="${hour}"]`);
        if (!slotEl) continue;

        // Sort events within the slot to ensure consistent placement
        eventsInSlot.sort((a, b) => a.EventTitle.localeCompare(b.EventTitle));

        const numOverlaps = eventsInSlot.length;

        eventsInSlot.forEach((event, index) => {
            const startMinute = parseInt(event.TimeRange.substring(3, 5), 10);
            const eventEl = document.createElement('div');
            
            // Determine Attendee information and colors
            const attendees = allSignups[event.id] || {};
            const attendeeEmails = Object.values(attendees).map(att => att.userEmail);
            const delegationEmails = Object.keys(delegationConfig);
            const isEveryone = delegationEmails.length > 0 && delegationEmails.every(email => attendeeEmails.includes(email));
            
            let bgColor, borderColor;
            if (isEveryone) {
                ({ color: bgColor, borderColor } = everyoneColorConfig);
            } else if (attendeeEmails.length > 0) {
                const firstAttendeeEmail = attendeeEmails.find(email => delegationConfig[email]);
                const firstAttendeeConfig = delegationConfig[firstAttendeeEmail];
                ({ color: bgColor, borderColor } = firstAttendeeConfig || { color: 'bg-gray-400', borderColor: 'border-gray-600' });
            } else {
                 ({ color: bgColor, borderColor } = { color: 'bg-gray-200 dark:bg-gray-600', borderColor: 'border-gray-400 dark:border-gray-500' });
            }
            
            eventEl.className = `calendar-event ${bgColor} ${borderColor}`;
            
            // Handle overlaps by adjusting width and horizontal position
            eventEl.style.width = `calc(${100 / numOverlaps}% - 2px)`;
            eventEl.style.left = `calc(${(100 / numOverlaps) * index}% + ${index * 1}px)`;
            eventEl.style.top = `${(startMinute / 60) * 100}%`;
            
            // Simplified height for now, assuming 1 hour duration. Can be made dynamic.
            eventEl.style.height = `95%`; 

            // Create attendee pills for visualization
            const attendeesHtml = delegationEmails
                .map(email => {
                    const userConfig = delegationConfig[email];
                    const isAttending = attendeeEmails.includes(email);
                    if (isAttending && userConfig) {
                        return `<div class="attendee-pill ${userConfig.color}" title="${userConfig.name}">${userConfig.name.charAt(0)}</div>`;
                    }
                    return '';
                })
                .join('');

            eventEl.innerHTML = `
                <div class="calendar-event-inner">
                    <span class="event-title">${event.EventTitle}</span>
                    <span class="event-location">${event.Location}</span>
                    <div class="event-attendees">${attendeesHtml}</div>
                </div>`;
            
            slotEl.appendChild(eventEl);
        });
    }
}
