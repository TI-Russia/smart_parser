using System.Collections.Generic;
using System.Linq;

namespace TI.Declarator.ParserCommon
{
    class VehicleEntry
    {
        public int Count {get; set;}
        public string Type { get; set; }
        public string Model { get; set; }

        public IEnumerable<Vehicle> GetVehicles()
        {
            var res = new List<Vehicle>();
            var v = new Vehicle(Model, Type);
            return Enumerable.Repeat(v, Count);
        }
    }
}
