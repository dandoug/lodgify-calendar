document.addEventListener("DOMContentLoaded", function () {
  const calendarElement = document.getElementById("calendar");
  const propertyId = calendarElement.dataset.propertyId
  const roomTypeId = calendarElement.dataset.roomTypeId
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
          priceSpan.textContent = `${apiData[date].price}`; // currency symbol is added by css

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

  async function fetchCalendarDates(startDate, signal) {
    const start = new Date(startDate);
    const end = addMonths(start, 2); // Calculate 2 months ahead
    const queryString = `?propertyId=${propertyId}&roomTypeId=${roomTypeId}` +
        `&startDate=${start.toISOString().split("T")[0]}&endDate=${end}`;
    const url = `${apiBaseUrl}/calendar-data` + queryString;

    const response = await fetch(url, { signal }); // Pass the signal here
    if (response.status !== 200) {
      const json = await response.json();
      console.error(`Failed to fetch calendar data: ${json.error}`);
      return undefined; // Handle fetch errors
    }
    const json = await response.json();
    return json.dates;
  }

  let activeFetch = null; // Keeps track of the active fetch in progress
  let requestCounter = 0;

  async function handleCalendarChange(instance) {
    const currentRequest = ++requestCounter; // Increment counter for each new request
    const currentMonth = instance.currentMonth;
    const currentYear = instance.currentYear;
    const startDate = new Date(currentYear, currentMonth, 1);

    // Cancel previous fetch if it's still in progress
    if (activeFetch) {
      activeFetch.abort(); // Abort the previous request
    }

    const abortController = new AbortController();
    activeFetch = abortController;

    try {
      const apiData = await fetchCalendarDates(startDate, abortController.signal); // Pass signal
      if (requestCounter === currentRequest) { // Ensure this is still the latest request
        if (apiData === undefined) {
          console.error("Failed to fetch calendar data.");
        } else {
          updateCalendarDays(instance, apiData);
        }
      }
    } catch (err) {
      if (err.name === "AbortError") {
        console.log("Fetch aborted; skipping update.");
      } else {
        console.error("Error during fetch:", err);
      }
    } finally {
      // Clear the active fetch if complete
      if (activeFetch === abortController) {
        activeFetch = null;
      }
    }
  }

  // Function to determine the number of months to show based on screen size
  function getShowMonths() {
    return window.innerWidth < 640 ? 1 : 2;
  }

  const debouncedHandleCalendarChange = debounce(async function (instance) {
    await handleCalendarChange(instance);
  }, 300); // 300ms delay

  // Variable to keep track of the Flatpickr instance and current showMonths
  let calendarInstance;
  let currentShowMonths = getShowMonths(); // Initialize with current screen size value

  // Function to initialize or reinitialize the Flatpickr calendar
  function initializeCalendar() {
    let defaultDate = null;

    // Capture the current state of the calendar (leftmost visible month) before destroying it
    if (calendarInstance) {
      const currentMonth = calendarInstance.currentMonth; // 0-based month index
      const currentYear = calendarInstance.currentYear; // Year value
      // Track the leftmost visible date
      defaultDate = new Date(currentYear, currentMonth, 1);
      calendarInstance.destroy();
    }

    // Recreate the Flatpickr instance
    calendarInstance = flatpickr("#calendar", {
      inline: true,
      showMonths: currentShowMonths, // Use current screen size mode
      defaultDate: defaultDate || new Date(), // Preserve the visible month or fallback to today
      enable: [],
      // Fetch days asynchronously, but ensure the visible month is set synchronously
      onReady: async function (selectedDates, dateStr, instance) {
        const startDate = defaultDate || new Date(); // Use stored date or fallback to today
        startDate.setDate(1); // Ensure it's the first day of the month
        // Jump to the correct month immediately BEFORE the API call finishes
        instance.jumpToDate(startDate);

        // Fetch backend data asynchronously
        const apiData = await fetchCalendarDates(startDate);
        if (apiData === undefined) {
          console.error("Failed to fetch calendar data.");
        } else {
          // Update the days asynchronously once data is ready
          updateCalendarDays(instance, apiData);
        }
      },
      onMonthChange: async function (selectedDates, dateStr, instance) {
        debouncedHandleCalendarChange(instance);
      },
      onYearChange: async function (selectedDates, dateStr, instance) {
        debouncedHandleCalendarChange(instance);
      },
    });

    // Immediately jump to the correct month after initialization
    if (defaultDate) {
      calendarInstance.jumpToDate(defaultDate); // Ensure Flatpickr immediately aligns with the tracked visible month
    }
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
