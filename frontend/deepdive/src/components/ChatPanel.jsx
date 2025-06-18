
// import React from "react";
// import { Volume2, Copy, ChevronUp } from "lucide-react";
// import { motion } from "framer-motion";
// import { Button } from "@/components/ui/button";

// const ChatPanel = () => {
//   return (
//     <div className="h-full flex flex-col">
//       <div className="p-4 border-b border-gray-200">
//         <h2 className="text-lg font-semibold text-red-600">Chat</h2>
//       </div>
      
//       <div className="flex-1 overflow-y-auto p-4">
//         <motion.div
//           initial={{ opacity: 0, y: 20 }}
//           animate={{ opacity: 1, y: 0 }}
//           transition={{ duration: 0.5 }}
//           className="flex justify-center mb-8"
//         >
//           <div className="inline-flex items-center bg-amber-100 rounded-full px-4 py-2">
//             <div className="w-6 h-6 bg-amber-300 rounded-full flex items-center justify-center mr-2">
//               <span className="text-amber-800">💡</span>
//             </div>
//             <span className="text-sm font-medium">Large Language Models in Scientific Discovery</span>
//           </div>
//         </motion.div>
        
//         <div className="mb-6">
//           <h3 className="text-lg font-semibold mb-2">Overview</h3>
//           <p className="text-sm text-gray-700">
//             Overview content
//             {/* Lorem ipsum dolor sit amet, quo ut volutpat salutatus. Lucilius prodesset mei no, 
//             et eros obvius sapientem vim. Eu etiam volumus has, has cu modo temporibus. 
//             Te dico putant aliqua per. Aperiri voluptatum vituperata in eam. Sit et facete 
//             iudicabit comprehensam, cibo ignota legimus duo ex.
//              */}
//           </p>
//         </div>
        
//         <div className="flex space-x-2 mt-8">
//           <Button variant="outline" size="sm" className="flex items-center">
//             <span className="mr-1">📝</span> Add Note
//           </Button>
//           <Button variant="outline" size="sm" className="flex items-center">
//             <Volume2 className="h-4 w-4 mr-1" /> Panel Audio
//           </Button>
//           <Button variant="outline" size="sm" className="flex items-center">
//             <Copy className="h-4 w-4 mr-1" /> Copy Overview
//           </Button>
//         </div>
//       </div>
      
//       <div className="border-t border-gray-200 p-4">
//         <div className="relative">
//           <input
//             type="text"
//             placeholder="start typing..."
//             className="w-full border border-gray-300 rounded-md py-2 px-4 pr-10 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
//           />
//           <div className="absolute right-3 top-2">
//             <ChevronUp className="h-5 w-5 text-gray-400" />
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default ChatPanel;


import React from "react";
import { Volume2, Copy, ChevronUp } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

const ChatPanel = () => {
  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-red-600">Chat</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex justify-center mb-8"
        >
          <div className="inline-flex items-center bg-amber-100 rounded-full px-4 py-2">
            <div className="w-6 h-6 bg-amber-300 rounded-full flex items-center justify-center mr-2">
              <span className="text-amber-800">💡</span>
            </div>
            <span className="text-sm font-medium">Large Language Models in Scientific Discovery</span>
          </div>
        </motion.div>
        
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-2">Overview</h3>
          <p className="text-sm text-gray-700">
            Overview content
            {/* Lorem ipsum dolor sit amet, quo ut volutpat salutatus. Lucilius prodesset mei no, 
            et eros obvius sapientem vim. Eu etiam volumus has, has cu modo temporibus. 
            Te dico putant aliqua per. Aperiri voluptatum vituperata in eam. Sit et facete 
            iudicabit comprehensam, cibo ignota legimus duo ex.
             */}
          </p>
        </div>
        
        <div className="flex space-x-2 mt-8">
          <Button variant="outline" size="sm" className="flex items-center">
            <span className="mr-1">📝</span> Add Note
          </Button>
          <Button variant="outline" size="sm" className="flex items-center">
            <Volume2 className="h-4 w-4 mr-1" /> Panel Audio
          </Button>
          <Button variant="outline" size="sm" className="flex items-center">
            <Copy className="h-4 w-4 mr-1" /> Copy Overview
          </Button>
        </div>
      </div>
      
      <div className="border-t border-gray-200 p-4">
        <div className="relative">
          <input
            type="text"
            placeholder="start typing..."
            className="w-full border border-gray-300 rounded-md py-2 px-4 pr-10 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
          <div className="absolute right-3 top-2">
            <ChevronUp className="h-5 w-5 text-gray-400" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
