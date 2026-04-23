
import React, { useEffect, useState } from 'react';
import { Clock, Trash2, BellRing, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Reminder {
  id: string;
  title: string;
  dateTime: string;
  triggered: boolean;
}

const Reminders: React.FC = () => {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [title, setTitle] = useState('');
  const [dateTime, setDateTime] = useState('');
  const [notification, setNotification] = useState<{ id: string; title: string } | null>(null);

  // Load reminders from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('reminders');
    if (saved) {
      try {
        setReminders(JSON.parse(saved));
      } catch (error) {
        console.error('Failed to load reminders:', error);
      }
    }
  }, []);

  // Save reminders to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('reminders', JSON.stringify(reminders));
  }, [reminders]);

  // Check for triggered reminders every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date().getTime();
      reminders.forEach((reminder) => {
        const reminderTime = new Date(reminder.dateTime).getTime();
        if (reminderTime <= now && !reminder.triggered) {
          // Trigger notification
          setNotification({ id: reminder.id, title: reminder.title });
          
          // Update reminder as triggered
          setReminders((prev) =>
            prev.map((r) =>
              r.id === reminder.id ? { ...r, triggered: true } : r
            )
          );

          // Auto-dismiss notification after 5 seconds
          setTimeout(() => {
            setNotification(null);
          }, 5000);
        }
      });
    }, 10000); // Check every 10 seconds

    return () => clearInterval(interval);
  }, [reminders]);

  const addReminder = () => {
    if (!title.trim() || !dateTime) {
      alert('Please enter a reminder title and date/time');
      return;
    }

    const newReminder: Reminder = {
      id: Date.now().toString(),
      title,
      dateTime,
      triggered: false,
    };

    setReminders([...reminders, newReminder]);
    setTitle('');
    setDateTime('');
  };

  const deleteReminder = (id: string) => {
    setReminders(reminders.filter((r) => r.id !== id));
  };

  const upcomingReminders = reminders
    .filter((r) => !r.triggered)
    .sort((a, b) => new Date(a.dateTime).getTime() - new Date(b.dateTime).getTime());
  
  const triggeredReminders = reminders.filter((r) => r.triggered);

  const formatDateTime = (dateTimeString: string) => {
    const date = new Date(dateTimeString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  };

  const getTimeUntil = (dateTimeString: string) => {
    const now = new Date().getTime();
    const reminderTime = new Date(dateTimeString).getTime();
    const diff = reminderTime - now;

    if (diff < 0) return 'Time passed';

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) return `In ${days}d ${hours}h`;
    if (hours > 0) return `In ${hours}h ${minutes}m`;
    return `In ${minutes}m`;
  };

  return (
    <>
      {/* Notification Popup */}
      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className="fixed top-4 right-4 z-50 bg-gradient-to-r from-yellow-500 to-yellow-600 text-white px-6 py-4 rounded-lg shadow-2xl flex items-center gap-4 backdrop-blur-md border border-yellow-400/50"
          >
            <BellRing size={24} className="animate-bounce" />
            <div>
              <p className="font-bold text-lg">Reminder!</p>
              <p className="text-sm text-yellow-100">{notification.title}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-extrabold gradient-text mb-2">Reminders</h1>
          <p className="text-lg text-gray-300">
            Set reminders for important documents and tasks. You'll receive a notification at the scheduled time.
          </p>
        </div>

        {/* Add Reminder Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-glass rounded-xl p-8 shadow-glow border border-bg3"
        >
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Clock size={24} />
            Create New Reminder
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">
                Reminder Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Review contract with ClientX"
                className="w-full px-4 py-3 rounded-lg bg-bg1 text-white border border-bg3 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">
                Date & Time
              </label>
              <input
                type="datetime-local"
                value={dateTime}
                onChange={(e) => setDateTime(e.target.value)}
                className="w-full px-4 py-3 rounded-lg bg-bg1 text-white border border-bg3 focus:outline-none focus:ring-2 focus:ring-primary transition-all cursor-pointer"
              />
              <p className="text-xs text-gray-400 mt-2">
                Select a date and time when you want to be reminded.
              </p>
            </div>

            <button
              onClick={addReminder}
              className="w-full px-6 py-3 rounded-lg bg-gradient-to-r from-primary via-accent to-green text-white font-bold hover:scale-105 transition-all shadow-glow"
            >
              Add Reminder
            </button>
          </div>
        </motion.div>

        {/* Upcoming Reminders */}
        {upcomingReminders.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Clock size={24} className="text-primary" />
              Upcoming Reminders ({upcomingReminders.length})
            </h2>

            <div className="space-y-4">
              {upcomingReminders.map((reminder) => (
                <motion.div
                  key={reminder.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="bg-glass rounded-xl p-6 shadow-glow border border-bg3 hover:border-primary transition-all flex items-start justify-between group"
                >
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white mb-2">{reminder.title}</h3>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-400">
                        <span className="font-semibold">When:</span> {formatDateTime(reminder.dateTime)}
                      </p>
                      <p className="text-sm text-primary font-semibold">
                        ⏱ {getTimeUntil(reminder.dateTime)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => deleteReminder(reminder.id)}
                    className="p-2 hover:bg-red-500/20 rounded transition-all text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 size={18} />
                  </button>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Triggered Reminders */}
        {triggeredReminders.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h2 className="text-2xl font-bold text-gray-400 mb-6 flex items-center gap-2">
              <AlertCircle size={24} />
              Triggered Reminders ({triggeredReminders.length})
            </h2>

            <div className="space-y-4">
              {triggeredReminders.map((reminder) => (
                <motion.div
                  key={reminder.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="bg-gray-900/50 rounded-xl p-6 shadow-glow border border-gray-700 flex items-start justify-between group"
                >
                  <div className="flex-1 opacity-60">
                    <h3 className="text-lg font-semibold text-gray-400 mb-2 line-through">
                      {reminder.title}
                    </h3>
                    <p className="text-sm text-gray-500">
                      Triggered on: {formatDateTime(reminder.dateTime)}
                    </p>
                  </div>
                  <button
                    onClick={() => deleteReminder(reminder.id)}
                    className="p-2 hover:bg-red-500/20 rounded transition-all text-red-400"
                  >
                    <Trash2 size={18} />
                  </button>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Empty State */}
        {reminders.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-glass rounded-xl p-16 text-center border border-bg3"
          >
            <Clock size={56} className="mx-auto text-gray-400 mb-4" />
            <h2 className="text-2xl font-bold text-gray-300 mb-2">No Reminders Yet</h2>
            <p className="text-gray-400 mb-6">
              Create your first reminder to stay on top of important tasks and documents.
            </p>
          </motion.div>
        )}
      </div>
    </>
  );
};

export default Reminders;
