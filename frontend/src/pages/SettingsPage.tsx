// Settings page — profile, notifications, data export

import { useState } from "react";
import { useAuthStore } from "@/store/auth-store";
import { authService } from "@/services/auth.service";
import { notificationService } from "@/services/notification.service";
import { exportService } from "@/services/export.service";
import { todayString } from "@/lib/utils";
import { Settings, Bell, Download, User } from "lucide-react";

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [timezone, setTimezone] = useState(user?.timezone || "UTC");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const handleProfileSave = async () => {
    setSaving(true);
    try {
      const updated = await authService.updateProfile({ full_name: fullName, timezone });
      setUser(updated);
      setMessage("Profile updated!");
    } catch {
      setMessage("Failed to update profile.");
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(""), 3000);
    }
  };

  const handleExport = async () => {
    try {
      setMessage("Generating export...");
      // Export last 90 days
      const d = new Date();
      d.setDate(d.getDate() - 90);
      const startDate = d.toISOString().split("T")[0];
      const blob = await exportService.exportCsv(startDate, todayString());
      exportService.downloadBlob(blob, `health-tracker-export-${todayString()}.csv`);
      setMessage("Export downloaded!");
    } catch {
      setMessage("Export failed.");
    }
    setTimeout(() => setMessage(""), 3000);
  };

  const handleTestEmail = async () => {
    try {
      const res = await notificationService.sendTestEmail();
      setMessage(res.message);
    } catch {
      setMessage("Failed to send test email.");
    }
    setTimeout(() => setMessage(""), 3000);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <Settings className="w-6 h-6 text-brand-500" />
        Settings
      </h2>

      {message && (
        <div className="bg-brand-50 text-brand-700 text-sm px-4 py-3 rounded-lg">{message}</div>
      )}

      {/* Profile Section */}
      <section className="bg-white rounded-xl border p-6">
        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <User className="w-5 h-5" /> Profile
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={user?.email || ""} disabled
              className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
            <input type="text" value={timezone} onChange={(e) => setTimezone(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none" />
          </div>
          <button onClick={handleProfileSave} disabled={saving}
            className="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors">
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </div>
      </section>

      {/* Notifications Section */}
      <section className="bg-white rounded-xl border p-6">
        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Bell className="w-5 h-5" /> Notifications
        </h3>
        <p className="text-sm text-gray-500 mb-4">Email notification settings</p>
        <button onClick={handleTestEmail}
          className="text-sm text-brand-600 hover:underline">
          Send test email →
        </button>
      </section>

      {/* Export Section */}
      <section className="bg-white rounded-xl border p-6">
        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Download className="w-5 h-5" /> Export Data
        </h3>
        <p className="text-sm text-gray-500 mb-4">Download your habit data as a CSV file.</p>
        <button onClick={handleExport}
          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2">
          <Download className="w-4 h-4" /> Export Last 90 Days (CSV)
        </button>
      </section>
    </div>
  );
}
