// ==UserScript==
// @name         Folkemødet Program Scraper (v1.4 - Smarter Load More)
// @namespace    http://tampermonkey.net/
// @version      1.4
// @description  Scrapes Folkemødet.dk. Stops "Load More" when button disappears/disabled. Names CSV by active day.
// @author       You
// @match        https://programoversigt.folkemoedet.dk/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';
    console.log("Folkemødet Scraper v1.4 initializing...");

    const PAGE_INTERACTION_DELAY_MS = 2500;
    const INITIAL_LOAD_DELAY_MS = 3000;
    const MAX_LOAD_MORE_SAFETY_ATTEMPTS = 30; // Increased safety net, actual stop is button disappearance
    let isExtracting = false;
    let daysDateMap = null;

    function ensureDaysDateMap() {
        if (daysDateMap) return daysDateMap;
        console.log("Attempting to parse days data from __NUXT_DATA__ for date mapping...");
        const nuxtDataScript = document.getElementById('__NUXT_DATA__');
        if (!nuxtDataScript || !nuxtDataScript.textContent) {
            console.warn("__NUXT_DATA__ script tag not found or empty. Date mapping will be unavailable.");
            daysDateMap = {}; return null;
        }
        try {
            const nuxtDataArray = JSON.parse(nuxtDataScript.textContent);
            for (const item of nuxtDataArray) {
                if (typeof item === 'string' && item.includes('"days":') && item.includes('"edges":')) {
                    try {
                        const parsedItem = JSON.parse(item);
                        if (parsedItem && parsedItem.days && parsedItem.days.edges) {
                            daysDateMap = {};
                            parsedItem.days.edges.forEach(edge => {
                                if (edge.node && edge.node.name && edge.node.date) {
                                    const simpleDayName = edge.node.name.trim().split(' ')[0].toLowerCase();
                                    daysDateMap[simpleDayName] = edge.node.date;
                                }
                            });
                            console.log("Days date map populated:", daysDateMap);
                            return daysDateMap;
                        }
                    } catch (e) { /* continue */ }
                }
            }
        } catch (e) { console.error("Error parsing __NUXT_DATA__ for days map:", e); }
        daysDateMap = {};
        console.warn("Could not find or parse 'days' data within __NUXT_DATA__ for date mapping.");
        return null;
    }

    function getActiveDayButton() {
        return document.querySelector('button.bg-aqua-deep-950.text-merino-50.font-semibold');
    }

    function extractSimpleDayNameFromButton(buttonElement) {
        if (!buttonElement || !buttonElement.textContent) return 'unknown_day';
        let dayText = '';
        const mobileDaySpan = buttonElement.querySelector('span.md\\:hidden');
        if (mobileDaySpan && mobileDaySpan.textContent.trim()) {
            dayText = mobileDaySpan.textContent.trim();
        } else {
            const desktopDaySpan = buttonElement.querySelector('span.hidden.md\\:block');
            if (desktopDaySpan && desktopDaySpan.textContent.trim()) {
                dayText = desktopDaySpan.textContent.trim().split(' ')[0];
            } else {
                dayText = buttonElement.textContent.trim().split(' ')[0];
            }
        }
        return dayText.toLowerCase().replace(/\s+/g, '_').replace(/[^\wæøåÆØÅ\-]/gi, '') || 'unknown_day';
    }

    function scrapeEventCard(cardElement, targetDateStr) {
        try {
            const url = new URL(cardElement.href, window.location.origin).href;
            const titleElement = cardElement.querySelector('p.text-\\[20px\\].font-semibold');
            const title = titleElement ? titleElement.textContent.trim() : '';
            const summaryElement = cardElement.querySelector('p.mt-1.line-clamp-2');
            const summary = summaryElement ? summaryElement.textContent.trim() : '';
            const timeElements = cardElement.querySelectorAll('div.flex.items-center.space-x-1.text-\\[15px\\] time');
            const startTimeRaw = timeElements.length > 0 && timeElements[0].getAttribute('datetime') ? timeElements[0].getAttribute('datetime') : '';
            const endTimeRaw = timeElements.length > 1 && timeElements[1].getAttribute('datetime') ? timeElements[1].getAttribute('datetime') : startTimeRaw;
            const locationElement = cardElement.querySelector('div.mx-5.my-6 p.ml-1');
            const location = locationElement ? locationElement.textContent.trim() : '';

            return {
                title, location, startTime: startTimeRaw, endTime: endTimeRaw,
                day_date: targetDateStr || '', url, summary,
                organizers: '', theme: ''
            };
        } catch (e) {
            console.warn("Error scraping an individual event card:", e, cardElement);
            return null;
        }
    }

    async function scrapeAllVisibleEventsForDay(targetDateStr) {
        console.log(`Starting scrapeAllVisibleEventsForDay for date (used in day_date field): ${targetDateStr}`);
        let allEventsForDay = [];
        let loadMoreSafetyCounter = 0; // Renamed for clarity
        const eventCardSelector = 'section.bg-merino-50 div.grid a[href^="/events/"]';
        const loadMoreButtonSelector = 'div.mt-16 button.text-2xl.uppercase'; // Button that says "Vis flere events"
        const scrapedEventUrls = new Set();

        let initialCards = document.querySelectorAll(eventCardSelector);
        console.log(`Initial DOM query for event cards found: ${initialCards.length} cards.`);

        // Scrape initially visible cards
        initialCards.forEach(card => {
            const eventUrl = new URL(card.href, window.location.origin).href;
            if (!scrapedEventUrls.has(eventUrl)) {
                const eventData = scrapeEventCard(card, targetDateStr);
                if (eventData) {
                    allEventsForDay.push(eventData);
                    scrapedEventUrls.add(eventUrl);
                }
            }
        });
        console.log(`Scraped ${allEventsForDay.length} initial events.`);

        // Loop to click "Load More"
        while (loadMoreSafetyCounter < MAX_LOAD_MORE_SAFETY_ATTEMPTS) {
            const loadMoreButton = document.querySelector(loadMoreButtonSelector);

            if (loadMoreButton && !loadMoreButton.disabled && window.getComputedStyle(loadMoreButton).display !== 'none') {
                console.log(`"Vis flere events" button found (Attempt ${loadMoreSafetyCounter + 1}). Clicking...`);
                loadMoreButton.click();
                loadMoreSafetyCounter++;

                // Wait for new content to load
                await new Promise(resolve => setTimeout(resolve, PAGE_INTERACTION_DELAY_MS));

                const currentEventCards = document.querySelectorAll(eventCardSelector);
                let newEventsFoundInThisPass = 0;
                currentEventCards.forEach(card => {
                    const eventUrl = new URL(card.href, window.location.origin).href;
                    if (!scrapedEventUrls.has(eventUrl)) {
                        const eventData = scrapeEventCard(card, targetDateStr);
                        if (eventData) {
                            allEventsForDay.push(eventData);
                            scrapedEventUrls.add(eventUrl);
                            newEventsFoundInThisPass++;
                        }
                    }
                });
                console.log(`  Found ${newEventsFoundInThisPass} new events in this pass. Total for day now: ${allEventsForDay.length}`);
                if (newEventsFoundInThisPass === 0 && loadMoreSafetyCounter > 1) {
                    // If no new events were added after a click (and it's not the first "load more"),
                    // assume all are loaded or something stalled.
                    console.log("  No new events loaded after click, stopping 'Load More' loop.");
                    break;
                }
            } else {
                console.log("'Vis flere events' button not found, disabled, or hidden. Assuming all events loaded for this day.");
                break;
            }
        }
        if (loadMoreSafetyCounter >= MAX_LOAD_MORE_SAFETY_ATTEMPTS) {
            console.warn("  Reached max load more safety attempts.");
        }
        return allEventsForDay;
    }

    async function processAndDownload(dayNameForFilename, targetDate) {
        if (isExtracting) {
            console.log(`Extraction busy. Skipping for ${dayNameForFilename}.`);
            return;
        }
        isExtracting = true;
        console.log(`--- Attempting Full DOM Scraping (with Load More) ---\nFilename hint: ${dayNameForFilename}\nTarget date for day_date field: ${targetDate}`);

        try {
            const eventsForDay = await scrapeAllVisibleEventsForDay(targetDate);
            const finalFilename = `folkemoedet_program_${dayNameForFilename || 'data'}.csv`;
            convertToCSVAndDownload(eventsForDay, finalFilename);
        } catch(e) {
            console.error("Error during full DOM scraping process:", e);
            alert("An error occurred during data scraping. Check console.");
        } finally {
            isExtracting = false;
            console.log("--- Extraction attempt finished ---");
        }
    }

    function convertToCSVAndDownload(objArray, filename) {
        if (!objArray || objArray.length === 0) {
            console.warn("No data to convert to CSV for file:", filename);
            alert(`No event data found for download: ${filename}.`);
            return;
        }
        const array = objArray;
        let csvString = '';
        const headers = ["title", "location", "startTime", "endTime", "day_date", "url", "summary", "organizers", "theme"];
        csvString += headers.map(header => `"${header.replace(/"/g, '""')}"`).join(',') + '\r\n';

        for (let i = 0; i < array.length; i++) {
            let line = '';
            headers.forEach((header, index) => {
                if (index > 0) line += ',';
                let value = array[i][header] === null || array[i][header] === undefined ? '' : String(array[i][header]);
                value = value.replace(/"/g, '""');
                line += `"${value}"`;
            });
            csvString += line + '\r\n';
        }

        console.log("CSV string created for:", filename);
        try {
            const blob = new Blob(["\uFEFF" + csvString], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement("a");
            if (link.download !== undefined) {
                const url = URL.createObjectURL(blob);
                link.setAttribute("href", url);
                link.setAttribute("download", filename);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
                console.log("Download initiated for " + filename);
            } else { throw new Error("HTML5 download attribute not supported."); }
        } catch (e) {
            console.error("Error during CSV download process for " + filename + ":", e);
            alert("Error downloading CSV. Check console.");
        }
    }

    function setupDayButtonListeners() {
        if (!daysDateMap) ensureDaysDateMap();

        const buttonContainer = document.querySelector('section.bg-quarter-pearl-50.text-aqua-deep-950.border-b.border-gray-200.py-4 div.w-full.max-w-7xl div.flex.justify-center.items-center');

        if (buttonContainer) {
            const dayButtons = buttonContainer.querySelectorAll('button');
            console.log(`Found ${dayButtons.length} day filter buttons. Attaching listeners.`);
            dayButtons.forEach(button => {
                button.addEventListener('click', async function() {
                    if (isExtracting) {
                        console.log("Extraction busy. Ignoring click.");
                        return;
                    }
                    const clickedButton = this;
                    const dayNameForFilename = extractSimpleDayNameFromButton(clickedButton);
                    const targetDate = daysDateMap ? daysDateMap[dayNameForFilename] : null;

                    if (!targetDate && daysDateMap && Object.keys(daysDateMap).length > 0) {
                        console.warn(`Could not determine target date for clicked day: ${dayNameForFilename} from daysDateMap. CSV 'day_date' field may be inaccurate or empty.`);
                    } else if (!daysDateMap) {
                         console.warn(`daysDateMap is not populated. CSV 'day_date' field will be empty.`);
                    }

                    console.log(`User clicked day: ${dayNameForFilename}, Target date for CSV 'day_date' field: ${targetDate}. Waiting ${PAGE_INTERACTION_DELAY_MS}ms for page to update...`);

                    // Wait for their page to visually switch days and potentially load initial set of events for the new day
                    await new Promise(resolve => setTimeout(resolve, PAGE_INTERACTION_DELAY_MS));

                    await processAndDownload(dayNameForFilename, targetDate);
                });
            });
        } else {
            console.warn("Could not find the day filter button container. Re-extraction on click won't work.");
        }
    }

    window.addEventListener('load', () => {
        console.log("Folkemødet Scraper: Page fully loaded. Initializing Userscript v1.4...");
        setTimeout(async () => {
            console.log("Initial timeout executing...");
            ensureDaysDateMap();

            const initialActiveButton = getActiveDayButton();
            const initialDayName = extractSimpleDayNameFromButton(initialActiveButton);
            const initialTargetDate = daysDateMap && initialDayName !== 'unknown_day' ? daysDateMap[initialDayName] : null;

            console.log(`Initial load - Filename day: ${initialDayName}, Target date for 'day_date': ${initialTargetDate}. Mode: Full DOM Scrape with Load More`);
            await processAndDownload(initialDayName, initialTargetDate);

            setupDayButtonListeners();
        }, INITIAL_LOAD_DELAY_MS);
    }, { once: true });

})();
