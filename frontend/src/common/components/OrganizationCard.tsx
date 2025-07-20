import React from "react";

interface Organization {
  name: string;
  type: string;
  description: string;
}

interface OrganizationCardProps {
  organization: Organization;
}

export default function OrganizationCard({ organization }: OrganizationCardProps) {
  return (
    <div className="border rounded-lg overflow-hidden shadow p-4">
      <h3 className="font-semibold mb-1">{organization.name}</h3>
      <p className="text-gray-600 text-sm">{organization.type}</p>
      <p className="mt-2 text-gray-800">{organization.description}</p>
    </div>
  );
}

