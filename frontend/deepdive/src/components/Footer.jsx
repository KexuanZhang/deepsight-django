import React from "react";
import { motion } from "framer-motion";

const Footer = () => {
  return (
    <footer className="bg-white border-t border-gray-200 py-8">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <p className="text-lg font-semibold mb-4">Our Research</p>
            <ul className="space-y-2">
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Dailysight</span></li>
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Dailypaper</span></li>
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Dailysight</span></li>
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Dailypaper</span></li>
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Dailysight</span></li>
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Dailypaper</span></li>
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
            <p className="text-lg font-semibold mb-4">News</p>
            <ul className="space-y-2">
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Latest News</span></li>
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Trends</span></li>
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Trends</span></li>
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
          >
            <p className="text-lg font-semibold mb-4">Safety</p>
            <ul className="space-y-2">
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Safety Approach</span></li>
              <li><span className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">Security & Privacy</span></li>
            </ul>
          </motion.div>
        </div>

        <div className="mt-8 pt-8 border-t border-gray-200">
          <p className="text-sm text-center text-gray-500">© 2025, Huawei. All Rights Reserved.</p>
        </div>
      </div>
    </footer>
  );
};


export default Footer;
