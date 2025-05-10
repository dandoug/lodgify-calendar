/**
 * Initializes and manages a dynamic price availability calendar for Lodgify properties.
 * This calendar displays room availability and pricing information, with support for
 * responsive layout and data caching.  Accepts an options argument for additional confirgureation
 *
 * @param {string} calendarDivId - The ID of the HTML element where the calendar will be rendered (REQUIRED)*
 * @param {Object} [options] - Configuration options for the calendar (optional)
 * @param {number} [options.max_cache_size] - Maximum number of cached date ranges to store (default 12)
 * @param {number} [options.cache_ttl_minutes] - Time-to-live in minutes for cached data (default 5)
 * @param {boolean} [options.debug_mode] - Enable debug logging when true (default window.LODGIFY_CALENDAR_DEBUG_MODE || false)
 * @param {string} [options.api_base_url] - Base URL for the calendar API (default window.LODGIFY_CALENDAR_API_BASE_URL || 'http://localhost:3000')
 */
function lodgifyPriceAvailabilityCalendar(calendarDivId, options = {})  {

  const {
        max_cache_size = 12,
        cache_ttl_minutes = 5,
        debug_mode = window.LODGIFY_CALENDAR_DEBUG_MODE || false,
        api_base_url = window.LODGIFY_CALENDAR_API_BASE_URL || 'http://localhost:3000',
    } = options;


  const calendarElement = document.getElementById(calendarDivId);
  const propertyId = calendarElement.dataset.propertyId
  const roomTypeId = calendarElement.dataset.roomTypeId

  function debugLog(message, ...optionalParams) {
      if (debug_mode) {
          console.log(message, ...optionalParams);
      }
  }

  const resizeObserver = new ResizeObserver(() => {
      const newShowMonths = getShowMonths(); // Recompute based on container size
      if (newShowMonths !== currentShowMonths) {
          currentShowMonths = newShowMonths;
          initializeCalendar(); // Reinitialize with new showMonths
      }
  });
  resizeObserver.observe(calendarElement); // Watch the container for size changes

  // Add this cache to manage the fetched data
  const cache = new Map();

  // Function to create a unique cache key
  function createCacheKey(propertyId, roomTypeId, startDate, endDate) {
      return `${propertyId}-${roomTypeId}-${startDate}-${endDate}`;
  }

  // Function to fetch data with caching
  async function fetchWithCache(startDate, endDate, signal) {
      const cacheKey = createCacheKey(propertyId, roomTypeId, startDate, endDate);
      const now = Date.now();

      // Check if data exists in cache and is not expired
      if (cache.has(cacheKey)) {
          const {data, expiration} = cache.get(cacheKey);
          if (now < expiration) {
              debugLog("Using cached data for Lodgify calendar");
              return data; // Return cached data
          } else {
              cache.delete(cacheKey); // Remove stale entry
          }
      }

      // Fetch the data from the API if not in cache or expired
      const queryString = `?propertyId=${propertyId}&roomTypeId=${roomTypeId}&startDate=${startDate}&endDate=${endDate}`;
      const url = `${api_base_url}/calendar-data` + queryString;

      try {
          const response = await fetch(url, {signal});
          if (response.status !== 200) {
              const json = await response.json();
              console.error(`Failed to fetch calendar data: ${json.error}`);
              return undefined;
          }

          const json = await response.json();
          const data = json.dates;

          // Store fetched data in cache with an expiration time (5 minutes)
          cache.set(cacheKey, {data, expiration: now + cache_ttl_minutes * 60 * 1000});

          // Clean up the cache to ensure it only keeps the last 12 entries
          if (cache.size > max_cache_size) {
              const oldestKey = Array.from(cache.keys())[0];
              cache.delete(oldestKey);
          }

          return data;
      } catch (err) {
          console.error("Error while fetching data:", err);
          return undefined;
      }
  }

  function formatDateLocal(date) {
      if (!(date instanceof Date)) return null;
      const year = date.getFullYear();
      const month = (date.getMonth() + 1).toString().padStart(2, "0"); // Add leading zero
      const day = date.getDate().toString().padStart(2, "0"); // Add leading zero
      return `${year}-${month}-${day}`;
  }

  function updateCalendarDays(instance, fetchedData, retries = 10) {
      if (!instance.calendarContainer) {
          if (retries > 0) {
              setTimeout(() => updateCalendarDays(instance, fetchedData, retries - 1), 100);
          } else {
              console.error("Failed to update calendar days: calendarContainer is not ready.");
          }
          return;
      }

      const allDays = instance.calendarContainer.querySelectorAll(".flatpickr-day");

      // Loop over all calendar days and fill data
      allDays.forEach((day) => {
          const date = formatDateLocal(day.dateObj); // Format as 'yyyy-MM-dd'
          const dayNumber = day.textContent;

          day.innerHTML = ""; // Clear the current content

          // Apply the fetched data if available
          if (fetchedData[date]) {
              const dayData = fetchedData[date];
              if (dayData.available) {
                  day.classList.add("has-price");

                  const dayNumberSpan = document.createElement("span");
                  dayNumberSpan.classList.add("day-number");
                  dayNumberSpan.textContent = dayNumber;

                  const priceSpan = document.createElement("span");
                  priceSpan.classList.add("day-price");
                  priceSpan.textContent = `${dayData.price}`; // Add price

                  day.appendChild(dayNumberSpan);
                  day.appendChild(priceSpan);
              } else {
                  day.classList.add("unavailable");
                  day.textContent = dayNumber;
              }
          } else {
              // If no data is available, mark as unavailable
              day.classList.add("unavailable");
              day.textContent = dayNumber;
          }
      });
  }

  function addMonths(date, months) {
      const localDate = new Date(date.getTime()); // Clone the date to avoid mutation
      const targetMonth = localDate.getMonth() + months;
      const targetYear = localDate.getFullYear() + Math.floor(targetMonth / 12);
      const normalizedMonth = targetMonth % 12;

      // Set the date to the first day of the target month
      return new Date(targetYear, normalizedMonth, 1); // All in local time
  }

  // Update the fetchCalendarDates function to use the caching mechanism
  async function fetchCalendarDates(startDate, signal) {
      if (!(startDate instanceof Date)) {
          throw new RangeError(`Invalid startDate provided: ${startDate}`);
      }

      // Calculate the range based on the number of months to display
      const endDate = addMonths(startDate, Math.max(currentShowMonths, 2)); // At least 2 months

      // Format both the start and end dates as `yyyy-MM-dd` (local time zone)
      const startFormatted = formatDateLocal(startDate);
      const endFormatted = formatDateLocal(endDate);

      // fetch the new data using the cached version, if available
      debugLog(`Fetching calendar data for: ${startFormatted} to ${endFormatted}`);
      const fetchedData = await fetchWithCache(startFormatted, endFormatted, signal);

      if (!fetchedData) {
          console.error(`Failed to fetch data for range: ${startFormatted} to ${endFormatted}`);
          return {}; // Return empty data
      }

      return fetchedData; // Return newly fetched data
  }

  // Function to determine the number of months to show based on the container size
  function getShowMonths() {
      const calendarContainer = document.getElementById("calendar"); // Get the container element
      const containerWidth = calendarContainer.offsetWidth; // Use the container's width

      // Adjust logic based on the container size
      return containerWidth < 640 ? 1 : 2;
  }

  function getVisibleDateRange(instance) {
      const firstVisibleMonth = instance.currentMonth; // 0-based index for leftmost visible month
      const firstVisibleYear = instance.currentYear;

      // Begin at the start of the first visible month
      const startDate = new Date(firstVisibleYear, firstVisibleMonth, 1);

      // End date = last day of the last visible month
      const endDate = addMonths(startDate, instance.config.showMonths); // Add visible months
      endDate.setDate(0); // Move to the last day of the month

      return {start: startDate, end: endDate}; // Return both start and end of range
  }


  const debouncedHandleCalendarChange = debounce(async function (instance) {
      const visibleRange = getVisibleDateRange(instance); // Calculate accurate visible date range
      const apiData = await fetchCalendarDates(visibleRange.start, null); // Fetch for visible months
      if (apiData) {
          updateCalendarDays(instance, apiData); // Update calendar with fetched data
      }
  }, 300); // Debounce delay


  // Variable to keep track of the Flatpickr instance and current showMonths
  let calendarInstance;
  let currentShowMonths = getShowMonths(); // Initialize with current screen size value

  // Function to initialize or reinitialize the Flatpickr calendar
  function initializeCalendar() {
      let defaultDate;

      if (calendarInstance) {
          const currentMonth = calendarInstance.currentMonth;
          const currentYear = calendarInstance.currentYear;

          defaultDate = new Date(currentYear, currentMonth, 1); // Leftmost visible month
          calendarInstance.destroy(); // Destroy the existing instance
      } else {
          const today = new Date(); // Current local date
          defaultDate = new Date(today.getFullYear(), today.getMonth(), 1); // Start of the month
      }

      currentShowMonths = getShowMonths(); // Dynamically determine visible months

      calendarInstance = flatpickr("#calendar", {
          inline: true,
          showMonths: currentShowMonths, // Adjust dynamically
          defaultDate: defaultDate,
          enable: [],
          // Debounced handlers to ensure proper fetching & updates
          onReady: async function (selectedDates, dateStr, instance) {
              debouncedHandleCalendarChange(instance);
          },
          onMonthChange: async function (selectedDates, dateStr, instance) {
              debouncedHandleCalendarChange(instance);
          },
          onYearChange: async function (selectedDates, dateStr, instance) {
              debouncedHandleCalendarChange(instance);
          },
      });

      calendarInstance.jumpToDate(defaultDate); // Correct positioning
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
}
