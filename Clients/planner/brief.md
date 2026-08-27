# Task

Total project is two clients and one backend api. models of the api can be found in src/no_show_agent/api/pydantic_models.py

I want to write a comprehensive plan on how to build the planner client application. 

It should have a similar layout to the screenshot in examples/outlook_with_sidebar.png and be build according to the color palette shown in examples/umc_utrecht_color_palette.png. The layout should contain the following main components
- Header: header element with appname 'NoShow Planner'
- Right Sidebar: collapsible waitlist, sorted by datetime. Shows patient info.  
- left sidebar: 'Today' button and calendar select components with month view. Also collapsible.
- Main panel
    - Filter dropdown as seen in examples/outlook_filter_dropdown.png with options Day, Three Day, Working Week (mon - fri), Week (mon - sun), Month. Selection filters the calendar items shown and determines the calendar mode if the calendar view is active. Dropdown filter contains a divider and an option 'List' below that to toggle List and Calendar view. Calendar view is default and Week is the default selected dropdown value
    - Calendar view: Should display a Google Calendar like calendar filled with the CalendarItems retrieved from the API. Shows day, three day, working week, week, or month depending on the filter dropdown selection
    - List view: Displays a list of CalendarItems retrieved from the API as shown in examples/outlook_list.png. Shows the items of the day, three day, working week, week, or month depending on the filter dropdown selection
    - Clicking an appointment in calendar view or list view should pop up a info modal like in examples/outlook_edit_appointment.png with full info of the appointment and a edit and delete button. Delete deletes the appointment. Edit presents alternative datetimes to select for this appointment.
    - Appointments can also be dragged just as in google calendar (only in position, not in size/length)
    - Waitlist items should also be able to be dragged on open sections of the calendar to schedule them

Ground yourself in the current codebase, including the minimal api in src/no_show_agent/api that contains the current endpoints and pydantic models. Give me options for the best libraries to build this planner client application.