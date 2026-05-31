import { defineStore } from "pinia";
import { formatDate } from "@/utils/date.js";
import * as eventsApi from "@/api/events.js";
import { normalizeEvent, toApiEventPayload } from "@/utils/event-mapper.js";
import { sortEvents } from "@/utils/event-sort.js";

export const useCalendarStore = defineStore("calendar", {
  state: () => ({
    events: [],
    loading: false,
    loaded: false,
    error: "",
    currentDate: formatDate(new Date()),
    viewYear: new Date().getFullYear(),
    viewMonth: new Date().getMonth(),
  }),

  getters: {
    /** 当日日程：未完成在前，已完成在后，同组按开始时间升序 */
    todayEvents(state) {
      return sortEvents(
        state.events.filter((e) => e.start_time.startsWith(state.currentDate)),
      );
    },

    eventDates(state) {
      const dates = new Set();
      state.events.forEach((e) => {
        dates.add(e.start_time.slice(0, 10));
      });
      return dates;
    },

    hasEventsOnDate: (state) => (dateStr) => {
      return state.events.some((e) => e.start_time.startsWith(dateStr));
    },
  },

  actions: {
    setCurrentDate(date) {
      this.currentDate = date;
    },

    setViewMonth(year, month) {
      this.viewYear = year;
      this.viewMonth = month;
    },

    getEventById(id) {
      return this.events.find((e) => String(e.id) === String(id));
    },

    async fetchEvents(date) {
      if (date) this.currentDate = date;
      this.loading = true;
      this.error = "";

      try {
        const list = await eventsApi.listEvents();
        this.events = sortEvents((list || []).map(normalizeEvent));
        this.loaded = true;
        return this.events;
      } catch (err) {
        this.error = err.message || "加载日程失败";
        console.error("[calendar] fetchEvents failed", err);
        throw err;
      } finally {
        this.loading = false;
      }
    },

    /** 语音 Agent 一轮 turn.done 后刷新日程列表 */
    async syncAfterVoiceTurn() {
      const previousIds = new Set(this.events.map((event) => String(event.id)));
      const events = await this.fetchEvents(this.currentDate);
      const addedDates = [
        ...new Set(
          events
            .filter((event) => !previousIds.has(String(event.id)))
            .map((event) => event.start_time.slice(0, 10))
            .filter(Boolean),
        ),
      ];

      // 语音新建事件后，将日历焦点切到新增事件所属日期，避免列表仍停留在旧日期。
      if (addedDates.length === 1 && addedDates[0] !== this.currentDate) {
        const [year, month] = addedDates[0].split("-").map(Number);
        this.currentDate = addedDates[0];
        if (Number.isFinite(year) && Number.isFinite(month)) {
          this.setViewMonth(year, month - 1);
        }
      }

      return events;
    },

    async fetchEventById(id) {
      const cached = this.getEventById(id);
      if (cached) return cached;

      try {
        const raw = await eventsApi.getEvent(id);
        const event = normalizeEvent(raw);
        const index = this.events.findIndex((e) => String(e.id) === String(id));
        if (index === -1) {
          this.events.push(event);
        } else {
          this.events[index] = event;
        }
        this.events = sortEvents(this.events);
        return event;
      } catch (err) {
        console.error("[calendar] fetchEventById failed", err);
        throw err;
      }
    },

    async addEvent(event) {
      const payload = toApiEventPayload(event);
      const raw = await eventsApi.createEvent(payload);
      const newEvent = normalizeEvent(raw);
      this.events = sortEvents([...this.events, newEvent]);
      return newEvent;
    },

    async deleteEvent(id) {
      await eventsApi.deleteEvent(id);
      this.events = this.events.filter((e) => String(e.id) !== String(id));
    },

    /** 切换完成状态：PUT /api/events/{id} { completed } */
    async toggleEventComplete(id) {
      const index = this.events.findIndex((e) => String(e.id) === String(id));
      if (index === -1) return;

      const prevCompleted = this.events[index].completed;
      const nextCompleted = !prevCompleted;

      this.events[index].completed = nextCompleted;
      this.events = sortEvents(this.events);

      try {
        const raw = await eventsApi.updateEvent(id, { completed: nextCompleted });
        const updated = normalizeEvent(raw);
        const idx = this.events.findIndex((e) => String(e.id) === String(id));
        if (idx !== -1) {
          this.events[idx] = {
            ...updated,
            repeat_type: this.events[idx].repeat_type,
          };
        }
        this.events = sortEvents(this.events);
      } catch (err) {
        const idx = this.events.findIndex((e) => String(e.id) === String(id));
        if (idx !== -1) {
          this.events[idx].completed = prevCompleted;
        }
        this.events = sortEvents(this.events);
        throw err;
      }
    },

    async updateEvent(event) {
      const payload = toApiEventPayload(event);
      const raw = await eventsApi.updateEvent(event.id, payload);
      const updated = normalizeEvent(raw);
      const index = this.events.findIndex(
        (e) => String(e.id) === String(event.id),
      );
      if (index !== -1) {
        this.events[index] = {
          ...updated,
          repeat_type: event.repeat_type ?? this.events[index].repeat_type,
        };
        this.events = sortEvents(this.events);
      }
      return this.events[index];
    },
  },
});
