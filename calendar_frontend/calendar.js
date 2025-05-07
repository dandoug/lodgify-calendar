document.addEventListener("DOMContentLoaded", function () {
    const calendarElement = document.getElementById("calendar");

    function formatDate(date) {
        return date.toISOString().split("T")[0];
    }

    function updateCalendarDays(instance, apiData) {
        const allDays = instance.calendarContainer.querySelectorAll(".flatpickr-day");
        allDays.forEach((day) => {
            const date = formatDate(day.dateObj); // Get date in YYYY-MM-DD format
            const dayNumber = day.textContent; // Retrieve the day number as shown by Flatpickr

            day.innerHTML = ""; // Clear the day content to avoid conflicts

            if (apiData[date]) {
                if (!apiData[date].available) {
                    // Make unavailable dates visually distinct
                    day.classList.add("unavailable");
                    const dayNumberSpan = document.createElement("span");
                    dayNumberSpan.textContent = dayNumber;

                    const priceSpan = document.createElement("span");
                    day.appendChild(dayNumberSpan);
                    day.appendChild(priceSpan);

                } else {
                    // Add price data for available dates
                    day.classList.add("has-price");

                    // Create and append the day number and price
                    const dayNumberSpan = document.createElement("span");
                    dayNumberSpan.classList.add("day-number");
                    dayNumberSpan.textContent = dayNumber;

                    const priceSpan = document.createElement("span");
                    priceSpan.classList.add("day-price");
                    priceSpan.textContent = `$${apiData[date].price}`;

                    day.appendChild(dayNumberSpan);
                    day.appendChild(priceSpan);
                }
            } else {
                day.classList.add("unavailable"); // Default to unavailable for dates without data
                day.textContent = dayNumber; // Add back the day number
            }
        });
    }

    async function fetchCalendarDates(startDate) {
        // Helper function to calculate the end date by adding two months
        function addMonths(date, months) {
            const newDate = new Date(date); // Create a copy of the date
            newDate.setMonth(newDate.getMonth() + months);
            return newDate.toISOString().split("T")[0]; // Return in YYYY-MM-DD format
        }

        const start = new Date(startDate);
        const end = addMonths(start, 2); // Compute endDate by adding 2 months

        const url = `http://localhost:3000/calendar-data?startDate=${start.toISOString().split("T")[0]}&endDate=${end}`;

        const response = await fetch(url);
        const json = await response.json();
        return json.dates; // Return the dates object
    }

    // Helper function to handle month or year changes
    async function handleCalendarChange(instance) {
        const currentMonth = instance.currentMonth; // Get the current month displayed in Flatpickr
        const currentYear = instance.currentYear; // Get the current year displayed
        const startDate = new Date(currentYear, currentMonth, 1); // Construct the first day of the current month/year
        const apiData = await fetchCalendarDates(startDate); // Fetch data
        updateCalendarDays(instance, apiData); // Update calendar days
    }

    // Setup flatpickr
    flatpickr("#calendar", {
        inline: true, // Keeps it always visible
        showMonths: 2, // Displays two months side-by-side
        enable: [], // Disables date selection by default
        onReady: async function (selectedDates, dateStr, instance) {
            const startDate = new Date();
            startDate.setDate(1); // Start date defaults to the first day of the current month
            const apiData = await fetchCalendarDates(startDate); // Fetch data
            updateCalendarDays(instance, apiData); // Update calendar days
        },
        onMonthChange: async function (selectedDates, dateStr, instance) {
            await handleCalendarChange(instance); // Reuse shared logic
        },
        onYearChange: async function (selectedDates, dateStr, instance) {
            await handleCalendarChange(instance); // Reuse shared logic
        },
    });

});