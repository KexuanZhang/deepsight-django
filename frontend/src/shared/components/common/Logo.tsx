import React from "react";
import { motion } from "framer-motion";

const Logo = () => {
  return (
    <motion.h1 
      className="text-3xl font-bold text-gray-800"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      DeepDive
    </motion.h1>
  );
};

export default Logo;
