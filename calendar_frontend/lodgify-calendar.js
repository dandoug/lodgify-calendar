document.addEventListener("DOMContentLoaded", function () {
  const calendarElement = document.getElementById("calendar");
  const propertyId = calendarElement.dataset.propertyId
  const apiBaseUrl = window.LODGIFY_CALENDAR_API_BASE_URL || 'http://localhost:3000';


  function formatDate(date) {
    return date.toISOString().split("T")[0];
  }

  function updateCalendarDays(instance, apiData, retries = 10) {
    if (!instance.calendarContainer) {
      if (retries > 0) {
        setTimeout(() => updateCalendarDays(instance, apiData, retries - 1), 100);
      } else {
        console.error("Failed to update calendar days: calendarContainer is not ready.");
      }
      return;
    }

    const allDays = instance.calendarContainer.querySelectorAll(".flatpickr-day");
    allDays.forEach((day) => {
      const date = formatDate(day.dateObj);
      const dayNumber = day.textContent;

      day.innerHTML = "";

      if (apiData[date]) {
        if (!apiData[date].available) {
          day.classList.add("unavailable");
          day.textContent = dayNumber;
        } else {
          day.classList.add("has-price");

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
        day.classList.add("unavailable");
        day.textContent = dayNumber;
      }
    });
  }

  function addMonths(date, months) {
    const newDate = new Date(date);
    newDate.setMonth(newDate.getMonth() + months);
    return newDate.toISOString().split("T")[0];
  }

  async function fetchCalendarDates(startDate) {
    const start = new Date(startDate);
    const end = addMonths(start, 2);
    const queryString = `?propertyId=${propertyId}&startDate=${start.toISOString().split("T")[0]}&endDate=${end}`;

    const url = `${apiBaseUrl}/calendar-data` + queryString;

    const response = await fetch(url);
    const json = await response.json();
    if (response.status !== 200)
      console.error(`Failed to fetch calendar data: ${json.error}`);
    return json.dates;
  }

  async function handleCalendarChange(instance) {
    const currentMonth = instance.currentMonth;
    const currentYear = instance.currentYear;
    const startDate = new Date(currentYear, currentMonth, 1);
    const apiData = await fetchCalendarDates(startDate);
    if (apiData === undefined) {
      console.error("Failed to fetch calendar data.");
    } else {
      updateCalendarDays(instance, apiData);
    }
  }

  // Function to determine the number of months to show based on screen size
  function getShowMonths() {
    return window.innerWidth < 640 ? 1 : 2;
  }

  // Variable to keep track of the Flatpickr instance and current showMonths
  let calendarInstance;
  let currentShowMonths = getShowMonths(); // Initialize with current screen size value

  // Function to initialize or reinitialize the Flatpickr calendar
  function initializeCalendar() {
    if (calendarInstance) {
      calendarInstance.destroy();
    }

    calendarInstance = flatpickr("#calendar", {
      inline: true,
      showMonths: currentShowMonths, // Use current number of months
      enable: [],
      onReady: async function (selectedDates, dateStr, instance) {
        const startDate = new Date();
        startDate.setDate(1);
        const apiData = await fetchCalendarDates(startDate);
        if (apiData === undefined) {
          console.error("Failed to fetch calendar data.");
        } else {
          setTimeout(() => {
            updateCalendarDays(instance, apiData);
          }, 0);
        }
      },
      onMonthChange: async function (selectedDates, dateStr, instance) {
        await handleCalendarChange(instance);
      },
      onYearChange: async function (selectedDates, dateStr, instance) {
        await handleCalendarChange(instance);
      },
    });
  }

  // Debounce function to limit event execution
  function debounce(fn, delay) {
    let timeout;
    return function (...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        fn(...args);
      }, delay);
    };
  }

  // Add debounced resize event listener with change detection
  const debouncedResize = debounce(() => {
    const newShowMonths = getShowMonths(); // Compute the new value of showMonths
    if (newShowMonths !== currentShowMonths) {
      // Only reinitialize if the number of months to show has changed
      currentShowMonths = newShowMonths; // Update the current value
      initializeCalendar(); // Reinitialize the calendar
    }
  }, 300);

  // Initialize the calendar for the first time
  initializeCalendar();

  // Attach the debounced resize listener
  window.addEventListener("resize", debouncedResize);
});
