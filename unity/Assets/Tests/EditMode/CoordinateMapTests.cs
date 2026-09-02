using NUnit.Framework;
using UnityEngine;

public class CoordinateMapTests
{
    [Test]
    public void OsToUnity_SwapsYAndZ()
    {
        Vector3 r = CoordinateMap.OsToUnity(1f, 2f, 3f);
        Assert.AreEqual(new Vector3(1f, 3f, 2f), r);
    }

    [Test]
    public void RoundTrip_PreservesPosition()
    {
        var p = new Vector3(4f, -2f, 7f);
        Assert.AreEqual(p, CoordinateMap.UnityToOs(CoordinateMap.OsToUnity(p)));
    }

    [Test]
    public void OsZ_IsUnityY_Up()
    {
        Vector3 up = CoordinateMap.OsToUnity(0f, 0f, 2f);
        Assert.IsTrue(up.y > 0f);
        Assert.AreEqual(0f, up.z);
    }

    [Test]
    public void OsY_IsUnityZ_Forward()
    {
        Vector3 fwd = CoordinateMap.OsToUnity(0f, 2f, 0f);
        Assert.IsTrue(fwd.z > 0f);
        Assert.AreEqual(0f, fwd.y);
    }
}