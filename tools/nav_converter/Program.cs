using System.Text.Json;
using ValveResourceFormat.NavMesh;

if (args.Length < 2)
{
    Console.WriteLine("Usage: nav_converter <input.nav> <output.json>");
    return;
}

var inputPath = args[0];
var outputPath = args[1];

var nav = new NavMeshFile();
nav.Read(inputPath);

var result = new
{
    version = nav.Version,
    subVersion = nav.SubVersion,

    areas = nav.Areas.Values.Select(area => new
    {
        id = area.AreaId,
        hull = area.HullIndex,

        corners = area.Corners.Select(corner => new
        {
            x = corner.X,
            y = corner.Y,
            z = corner.Z
        }),

        connections = area.Connections
            .SelectMany(direction => direction)
            .Select(connection => new
            {
                areaId = connection.AreaId,
                edgeId = connection.EdgeId
            })
            .ToArray(),

        laddersAbove = area.LaddersAbove,
        laddersBelow = area.LaddersBelow
    }).ToArray(),

    ladders = nav.Ladders.Select(ladder => new
    {
        id = ladder.Id,
        width = ladder.Width,
        length = ladder.Length,

        bottom = new
        {
            x = ladder.Bottom.X,
            y = ladder.Bottom.Y,
            z = ladder.Bottom.Z
        },

        top = new
        {
            x = ladder.Top.X,
            y = ladder.Top.Y,
            z = ladder.Top.Z
        }
    }).ToArray()
};

var options = new JsonSerializerOptions
{
    WriteIndented = true
};

var json = JsonSerializer.Serialize(
    result,
    options
);

Directory.CreateDirectory(
    Path.GetDirectoryName(
        Path.GetFullPath(outputPath)
    )!
);

File.WriteAllText(
    outputPath,
    json
);

Console.WriteLine($"NAV version: {nav.Version}");
Console.WriteLine($"Areas: {nav.Areas.Count}");
Console.WriteLine($"Ladders: {nav.Ladders.Length}");
Console.WriteLine($"Saved to: {Path.GetFullPath(outputPath)}");