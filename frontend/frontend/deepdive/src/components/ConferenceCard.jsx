import React from "react";

export function ConferenceCard({ conference }) {
  return (
    <div className="border rounded-lg overflow-hidden shadow p-4">
      <h3 className="font-semibold mb-1">{conference.name}</h3>
      <p className="text-gray-600 text-sm">{conference.location} • {conference.year}</p>
      <p className="mt-2 text-gray-800">{conference.summary}</p>
    </div>
  );
}

export default ConferenceCard;
